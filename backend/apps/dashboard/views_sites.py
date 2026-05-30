"""Staff console views for per-site alarm management and onboarding."""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import Perm
from apps.alarms.media import collect_related_event_media, resolve_picture_media_type
from apps.alarms.models import AlarmEvent as Event
from apps.alarms.tasks import (
    initial_site_discovery,
    refresh_hik_site_health,
    sync_hik_alarm_status,
    sync_hik_site_devices,
)
from apps.dashboard.console_auth import (
    generate_compliant_password,
    password_validation_user,
    validate_console_password,
)
from apps.dashboard.event_presenters import serialize_console_event
from apps.dashboard.billing_helpers import billing_day_from_due_date
from apps.dashboard.parsers import parse_date_field, parse_decimal_field, parse_int_field
from apps.dashboard.permissions import StaffRequiredMixin
from apps.dashboard.site_helpers import (
    assign_site_operations_zone,
    build_display_alarm_peripherals,
    build_active_faults,
    compute_alarm_inventory_counts,
    filter_installed_alarm_outputs,
    filter_installed_module_peripherals,
    normalize_zone_color,
    operations_zone_name_taken,
    operations_zones_for_site,
    visible_console_events,
)
from apps.hik_adapter.services import HikPartnerService
from apps.accounts.models import CustomerGroup
from apps.sites.models import (
    AlarmPanelDevice,
    CustomerSiteAccess,
    Site,
    Subsystem,
    Subscription,
    SubscriptionPackage,
    Zone,
)
from apps.sites.scenes import SCENE_OPTIONS, normalize_scene_label

class SiteConsoleView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/sites/console.html"

    def _fallback_panic_capability(self):
        return {
            "audible_enabled": False,
            "silent_enabled": False,
            "mode": "unavailable",
            "summary_message": "Panic capability could not be confirmed for this site.",
            "panels": [],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = get_object_or_404(Site.objects.select_related("operations_zone"), pk=self.kwargs["pk"])
        service = HikPartnerService()
        context["site"] = site
        context["can_manage_zones"] = user_has_console_permission(
            self.request.user, Perm.MANAGE_SITES
        )
        devices = AlarmPanelDevice.objects.filter(site=site).prefetch_related("subsystems__zones", "peripherals", "outputs")
        context["devices"] = devices
        context["devices_count"] = devices.count()
        context["hik_devices"] = site.hik_devices.all()
        context["hik_devices_count"] = site.hik_devices.count()
        online_control_area_count = sum(
            device.subsystems.count() or 1
            for device in devices
            if device.is_online
        )
        context["online_control_area_count"] = online_control_area_count
        context["has_online_control_areas"] = online_control_area_count > 0
        panic_capability = cache.get(f"site-panic-capability:{site.id}")
        if panic_capability is None:
            try:
                panic_capability = service.get_site_panic_capability(site)
            except Exception:
                panic_capability = self._fallback_panic_capability()
            cache.set(f"site-panic-capability:{site.id}", panic_capability, timeout=60)
        context["panic_capability"] = panic_capability
        display_alarm_peripherals = build_display_alarm_peripherals(site)
        context["alarm_peripherals"] = display_alarm_peripherals
        context["alarm_module_peripherals"] = filter_installed_module_peripherals(display_alarm_peripherals)
        context["alarm_outputs"] = filter_installed_alarm_outputs(site)
        context["inventory_counts"] = compute_alarm_inventory_counts(site, display_alarm_peripherals)
        recent_events = visible_console_events(site, limit=15)
        context["recent_events"] = recent_events
        context["recent_events_payload"] = [serialize_console_event(event) for event in recent_events]
        active_faults = build_active_faults(site)
        context["active_faults"] = active_faults[:5]
        context["active_faults_payload"] = active_faults[:5]
        context["active_fault_count"] = len(active_faults)
        context["system_faults"] = context["active_fault_count"]
        
        # Determine Aggregate Site Status
        context["site_status"] = service.get_site_status(site=site)
        status = "disarmed"
        for device in devices:
            for sub in device.subsystems.all():
                s = sub.status.lower()
                if s == "alarm":
                    status = "alarm"
                    break
                elif s == "armed" and status != "alarm":
                    status = "armed"
                elif s == "stay" and status not in ["alarm", "armed"]:
                    status = "stay"
            if status == "alarm": break
        context["aggregate_site_status"] = status
        
        # Dynamic Last Activity
        last_event = recent_events[0] if recent_events else None
        if last_event:
            name = last_event.zone.name if last_event.zone else (last_event.subsystem.name if last_event.subsystem else "System")
            # Use template_localtime to respect project settings
            local_time = timezone.template_localtime(last_event.occurred_at)
            context["last_activity"] = f"{name} ({local_time.strftime('%H:%M')})"
        else:
            context["last_activity"] = "No recent activity"

        try:
            context["subscription"] = site.subscription
        except Exception:
            context["subscription"] = None

        # Onboarding / access status. A site is only considered fully
        # customer-onboarded once it has a master owner account.
        context["existing_access"] = site.access_list.select_related("user").all()
        context["access_count"] = context["existing_access"].count()
        owner_access = [
            access
            for access in context["existing_access"]
            if access.role == CustomerSiteAccess.ROLE_OWNER
        ]
        context["owner_access_count"] = len(owner_access)
        context["has_owner_access"] = bool(owner_access)
        context["primary_owner_access"] = owner_access[0] if owner_access else None
        context["readiness"] = {
            "has_devices": context["devices_count"] > 0 or context["hik_devices_count"] > 0,
            "has_access": context["access_count"] > 0,
            "has_owner": context["has_owner_access"],
            "has_subscription": bool(context["subscription"]),
            "is_active": site.is_active,
        }
        
        return context
class SiteActionView(StaffRequiredMixin, View):
    def post(self, request, pk, action):
        site = get_object_or_404(Site, pk=pk)
        service = HikPartnerService()
        
        subsystem_id = request.POST.get("subsystem_id")
        if subsystem_id:
            from apps.sites.models import Subsystem
            subsystem = get_object_or_404(
                Subsystem.objects.select_related("device"),
                pk=subsystem_id,
                site=site,
            )
            try:
                if not subsystem.device.is_online:
                    messages.warning(
                        request,
                        f"{subsystem.name} skipped: panel is offline or unreachable. Refresh status after it reconnects.",
                    )
                    return redirect("dashboard:site-console", pk=pk)
                # Map internal action labels to Hik commands if needed
                cmd = action
                if action == "arm-away": cmd = "arm"
                elif action == "arm-stay": cmd = "stay-arm"
                
                service.execute_subsystem_command(site, subsystem, cmd)
                messages.success(request, f"{subsystem.name}: {action.replace('-', ' ').title()}")
            except Exception as e:
                if getattr(e, "error_code", None) == "LAP020011":
                    messages.warning(
                        request,
                        f"{subsystem.name} skipped: panel is offline or unreachable. Refresh status after it reconnects.",
                    )
                else:
                    messages.error(request, f"{subsystem.name} {action} failed: {str(e)}")
        
        elif action in ["arm-away", "arm-stay", "arm", "stay", "disarm", "clear-alarm"]:
            # Global command for all partitions
            count = 0
            failures = []
            skipped_offline = 0
            cmd = action
            if action == "arm-away":
                cmd = "arm"
            elif action == "arm-stay":
                cmd = "stay-arm"

            for panel in AlarmPanelDevice.objects.filter(site=site).prefetch_related("subsystems"):
                panel_subsystems = list(panel.subsystems.all())
                if not panel.is_online:
                    skipped_offline += len(panel_subsystems) or 1
                    continue
                for index, sub in enumerate(panel_subsystems):
                    try:
                        service.execute_subsystem_command(
                            site,
                            sub,
                            cmd,
                            requesting_user=request.user,
                        )
                        count += 1
                    except Exception as exc:
                        if getattr(exc, "error_code", None) == "LAP020011":
                            skipped_offline += len(panel_subsystems[index:]) or 1
                            break
                        failures.append(f"{sub.name}: {exc}")

            if count > 0:
                messages.success(request, f"Site {action.replace('-', ' ').title()} dispatched to {count} area{'s' if count != 1 else ''}.")
            if skipped_offline:
                messages.warning(
                    request,
                    f"Skipped {skipped_offline} offline or unreachable area{'s' if skipped_offline != 1 else ''}. Refresh status after panels reconnect.",
                )
            if failures:
                if count == 0:
                    messages.error(request, f"Global {action} failed: {failures[0]}")
                else:
                    messages.warning(request, f"{len(failures)} area{'s' if len(failures) != 1 else ''} did not accept the command.")
            if count == 0 and not failures and skipped_offline == 0:
                messages.warning(request, "No areas found to control.")
        
        elif action == "sync-devices":
            transaction.on_commit(lambda: sync_hik_site_devices.delay(str(site.pk)))
            messages.success(
                request,
                f"Device sync for {site.name} has started in the background.",
            )
        elif action == "sync-alarms":
            transaction.on_commit(lambda: sync_hik_alarm_status.delay(str(site.pk)))
            messages.success(
                request,
                f"Alarm and peripheral sync for {site.name} has started in the background.",
            )
        elif action == "refresh-health":
            transaction.on_commit(lambda: refresh_hik_site_health.delay(str(site.pk)))
            messages.success(
                request,
                f"Health refresh for {site.name} has started in the background.",
            )
        elif action == "panic":
            try:
                panic_type = request.POST.get("panic_type", "audible")
                if panic_type not in {"audible", "silent"}:
                    panic_type = "audible"
                panic_capability = service.get_site_panic_capability(site)
                cache.set(f"site-panic-capability:{site.id}", panic_capability, timeout=60)
                if panic_type == "silent" and not panic_capability.get("silent_enabled"):
                    messages.error(
                        request,
                        panic_capability.get("summary_message")
                        or "Silent panic is not supported for this site via Hik-Partner Pro.",
                    )
                    return redirect("dashboard:site-console", pk=pk)
                result = service.trigger_global_panic(site, panic_type=panic_type)
                label = "AUDIBLE" if panic_type == "audible" else "SILENT"
                dispatched = result.get("dispatched", 0)
                dispatched_partitions = result.get("dispatched_partitions", 0)
                failed_partitions = result.get("failed_partitions", 0)
                if dispatched:
                    messages.success(
                        request,
                        f"GLOBAL {label} PANIC DISPATCHED FOR {site.name} "
                        f"({dispatched} panel{'s' if dispatched != 1 else ''}, "
                        f"{dispatched_partitions} area{'s' if dispatched_partitions != 1 else ''})",
                    )
                    if failed_partitions:
                        messages.warning(
                            request,
                            f"{failed_partitions} area{'s' if failed_partitions != 1 else ''} did not accept the panic command.",
                        )
                elif failed_partitions:
                    messages.error(
                        request,
                        f"Global panic failed: {failed_partitions} area{'s' if failed_partitions != 1 else ''} rejected the command.",
                    )
                else:
                    messages.warning(request, "No online panels were available for panic dispatch.")
            except Exception as e:
                messages.error(request, f"Panic trigger failed: {str(e)}")

        return redirect("dashboard:site-console", pk=pk)

class GlobalSyncView(StaffRequiredMixin, View):
    def post(self, request):
        service = HikPartnerService()
        count = 0
        for site in Site.objects.all():
            try:
                service.sync_site_devices(site)
                service.sync_alarm_status(site)
                try:
                    service.refresh_site_health(site)
                except Exception:
                    pass
                count += 1
            except Exception:
                continue
        messages.success(request, f"Global infrastructure sync complete. {count} sites updated.")
        return redirect("dashboard:home")

class ProvisionSiteView(StaffRequiredMixin, View):
    def post(self, request):
        from apps.hik_adapter.services import HikPartnerError

        name = request.POST.get("name", "").strip()
        hik_site_id = request.POST.get("hik_site_id", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        country = request.POST.get("country", "").strip()
        timezone = request.POST.get("timezone", "UTC").strip()
        latitude = request.POST.get("latitude", "").strip()
        longitude = request.POST.get("longitude", "").strip()
        primary_industry = normalize_scene_label(request.POST.get("primary_industry", "").strip())
        secondary_industry = request.POST.get("secondary_industry", "").strip()

        if not name:
            messages.error(request, "Site name is required.")
            return redirect("dashboard:sites")

        try:
            latitude_value = parse_decimal_field(latitude, label="Latitude") if latitude else None
            longitude_value = parse_decimal_field(longitude, label="Longitude") if longitude else None
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:sites")

        service = HikPartnerService()

        # If no Hik site ID supplied, attempt to create the site on the Hik platform
        # and retrieve the assigned ID. Falls back gracefully if the client is not
        # configured or an error occurs.
        if not hik_site_id:
            if not service.client.is_configured():
                messages.error(
                    request,
                    "Hik Site ID is required when the Hik-Partner Pro integration is not configured.",
                )
                return redirect("dashboard:sites")
            try:
                hik_site_id = service.provision_hik_site(
                    name=name,
                    site_state=state or None,
                    site_city=city or None,
                    site_street=address or None,
                    location=address or None,
                )
                messages.info(request, f"Site created on Hik-Partner platform (ID: {hik_site_id}).")
            except HikPartnerError as exc:
                messages.error(request, f"Failed to create site on Hik platform: {exc}")
                return redirect("dashboard:sites")

        site, created = Site.objects.get_or_create(
            hik_site_id=hik_site_id,
            defaults={
                "name": name,
                "address": address,
                "city": city,
                "state": state,
                "country": country,
                "timezone": timezone,
                "latitude": latitude_value,
                "longitude": longitude_value,
                "primary_industry": primary_industry,
                "secondary_industry": secondary_industry,
            },
        )

        if created:
            assign_site_operations_zone(site, request.POST.get("operations_zone", ""))
            site.save(update_fields=["operations_zone"])
            messages.success(request, f"Site '{name}' provisioned successfully.")
            transaction.on_commit(lambda: initial_site_discovery.delay(str(site.pk)))
            messages.info(
                request,
                "Initial infrastructure discovery has started in the background. "
                "Devices and live status will appear as the Hik sync completes.",
            )
            
            # CONSID: If this is a new setup, take them straight to client onboarding
            return redirect(f"{reverse('dashboard:onboard-client', args=[site.pk])}?init=true")
        else:
            messages.info(request, f"Site with Hik ID '{hik_site_id}' already exists.")

        return redirect("dashboard:site-console", pk=site.pk)

class UpdateSiteView(StaffRequiredMixin, View):
    template_name = "dashboard/sites/update.html"

    def get(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        return render(
            request,
            self.template_name,
            {
                "site": site,
                "scene_options": SCENE_OPTIONS,
                "operations_zones": operations_zones_for_site(site),
            },
        )

    def post(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        name = request.POST.get("name", "").strip()
        hik_site_id = request.POST.get("hik_site_id", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Display name is required.")
            return redirect("dashboard:update-site", pk=pk)

        if (
            hik_site_id
            and Site.objects.exclude(pk=site.pk).filter(hik_site_id=hik_site_id).exists()
        ):
            messages.error(request, f"Hik site ID '{hik_site_id}' is already assigned to another site.")
            return redirect("dashboard:update-site", pk=pk)

        try:
            latitude_value = parse_decimal_field(
                request.POST.get("latitude", "").strip(),
                label="Latitude",
            ) if request.POST.get("latitude", "").strip() else None
            longitude_value = parse_decimal_field(
                request.POST.get("longitude", "").strip(),
                label="Longitude",
            ) if request.POST.get("longitude", "").strip() else None
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:update-site", pk=pk)

        site.name = name
        if hik_site_id:
            site.hik_site_id = hik_site_id
        
        site.address = request.POST.get("address", "").strip()
        site.city = request.POST.get("city", "").strip()
        site.state = request.POST.get("state", "").strip()
        site.country = request.POST.get("country", "").strip()
        site.timezone = request.POST.get("timezone", "UTC").strip()
        site.latitude = latitude_value
        site.longitude = longitude_value
        site.primary_industry = normalize_scene_label(request.POST.get("primary_industry", "").strip())
        site.secondary_industry = request.POST.get("secondary_industry", "").strip()
        assign_site_operations_zone(site, request.POST.get("operations_zone", ""))
        site.is_active = is_active
        site.save()

        if site.latitude is None or site.longitude is None:
            HikPartnerService().geocode_site_location(site)
        
        messages.success(request, f"Updated configuration for {site.name}")
        return redirect("dashboard:site-console", pk=pk)

class HikAddDeviceView(StaffRequiredMixin, View):
    """
    Console-side bridge for adding a device to the Hik-Partner Pro platform.
    Calls HikPartnerService.add_devices_to_hik_site() which also syncs local DB.
    """

    def post(self, request, pk):
        from apps.hik_adapter.services import HikPartnerError

        site = get_object_or_404(Site, pk=pk)
        serial = request.POST.get("device_serial", "").strip()
        validate_code = request.POST.get("validate_code", "").strip()

        if not serial or not validate_code:
            messages.error(request, "Device serial number and validation code are required.")
            return redirect("dashboard:site-console", pk=pk)

        service = HikPartnerService()
        try:
            result = service.add_devices_to_hik_site(
                site=site,
                device_list=[{"deviceSerial": serial, "validateCode": validate_code}],
            )
            success_list = result.get("addSuccessList", [])
            failed_list = result.get("addFailedList", [])
            if success_list:
                messages.success(request, f"Device '{serial}' added to Hik platform. Devices synced.")
            if failed_list:
                reason = failed_list[0].get("failReason", "unknown error")
                messages.error(request, f"Hik platform rejected device '{serial}': {reason}")
        except HikPartnerError as exc:
            messages.error(request, f"Failed to add device: {exc}")

        return redirect("dashboard:site-console", pk=pk)


class HikRemoveDeviceView(StaffRequiredMixin, View):
    """
    Console-side bridge for removing a device from the Hik-Partner Pro platform
    and deleting its local records.
    """

    def post(self, request, pk):
        from apps.hik_adapter.services import HikPartnerError

        site = get_object_or_404(Site, pk=pk)
        hik_device_id = request.POST.get("hik_device_id", "").strip()

        if not hik_device_id:
            messages.error(request, "Hik device ID is required.")
            return redirect("dashboard:site-console", pk=pk)

        service = HikPartnerService()
        try:
            service.remove_device_from_hik(hik_device_id)
            messages.success(request, f"Device '{hik_device_id}' removed from Hik platform.")
        except HikPartnerError as exc:
            messages.error(request, f"Failed to remove device: {exc}")

        return redirect("dashboard:site-console", pk=pk)


class RegisterPanelView(StaffRequiredMixin, View):
    """
    Manually register an AX Pro (or any alarm panel) for a site.
    Used when auto-sync via Hik-Partner does not return the panel,
    or when the operator knows the serial number and wants to add it directly.
    """

    def post(self, request, pk):
        from apps.sites.models import AlarmPanelDevice
        site = get_object_or_404(Site, pk=pk)
        name = request.POST.get("name", "").strip()
        serial_number = request.POST.get("serial_number", "").strip()
        hik_device_id = request.POST.get("hik_device_id", "").strip() or serial_number

        if not name or not serial_number:
            messages.error(request, "Panel name and serial number are required.")
            return redirect("dashboard:site-console", pk=pk)

        if AlarmPanelDevice.objects.filter(serial_number=serial_number).exists():
            messages.warning(request, f"A panel with serial '{serial_number}' is already registered.")
            return redirect("dashboard:site-console", pk=pk)

        AlarmPanelDevice.objects.create(
            site=site,
            name=name,
            serial_number=serial_number,
            hik_device_id=hik_device_id,
            device_type=AlarmPanelDevice.DEVICE_TYPE_PANEL,
            is_online=False,
        )
        messages.success(
            request,
            f"Panel '{name}' registered. Use 'Refresh Status' to pull live partition and zone data.",
        )
        return redirect("dashboard:site-console", pk=pk)


class SiteDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        confirmation = request.POST.get("confirm_name", "").strip()
        if confirmation != site.name:
            messages.error(request, "Type the exact site name to delete it.")
            return redirect("dashboard:update-site", pk=pk)

        site_name = site.name
        site.delete()
        messages.success(request, f"Site '{site_name}' and its related records were deleted.")
        return redirect("dashboard:sites")


class OnboardClientView(StaffRequiredMixin, View):
    template_name = "dashboard/sites/onboard.html"

    def get(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        existing_access = CustomerSiteAccess.objects.filter(site=site).select_related("user")
        has_owner_access = existing_access.filter(role=CustomerSiteAccess.ROLE_OWNER).exists()
        access_management_mode = has_owner_access and request.GET.get("init") != "true"
        pkgs = list(SubscriptionPackage.objects.filter(is_active=True).order_by("monthly_rate"))
        return render(request, self.template_name, {
            "site": site,
            "existing_access": existing_access,
            "has_owner_access": has_owner_access,
            "access_management_mode": access_management_mode,
            "default_role": CustomerSiteAccess.ROLE_MANAGER if access_management_mode else CustomerSiteAccess.ROLE_OWNER,
            "has_subscription": Subscription.objects.filter(site=site).exists(),
            "customers": User.objects.filter(is_staff=False).order_by("username"),
            "packages": pkgs,
            "packages_json": json.dumps([
                {"id": str(p.id), "rate": str(p.monthly_rate), "grace": p.grace_period_days}
                for p in pkgs
            ]),
        })

    def post(self, request, pk):
        import secrets
        from django.contrib.auth.models import User
        from apps.accounts.models import CustomerProfile

        site = get_object_or_404(Site, pk=pk)
        has_owner_access_before = CustomerSiteAccess.objects.filter(
            site=site,
            role=CustomerSiteAccess.ROLE_OWNER,
        ).exists()
        access_management_mode = has_owner_access_before

        # -- Client account details --
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role", CustomerSiteAccess.ROLE_OWNER).strip()
        can_control = request.POST.get("can_control_alarm") == "on"

        # -- Subscription details (optional) --
        package_id = request.POST.get("package_id", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        next_due_date = request.POST.get("next_due_date", "").strip()
        billing_day = request.POST.get("billing_day", "").strip()
        grace_period_days = request.POST.get("grace_period_days", request.POST.get("grace_period", "7")).strip()

        if not email:
            messages.error(request, "Email is required.")
            return redirect("dashboard:onboard-client", pk=pk)

        valid_roles = {
            CustomerSiteAccess.ROLE_OWNER,
            CustomerSiteAccess.ROLE_MANAGER,
            CustomerSiteAccess.ROLE_VIEWER,
        }
        if role not in valid_roles:
            messages.error(request, "Please choose a valid access role.")
            return redirect("dashboard:onboard-client", pk=pk)

        if role == CustomerSiteAccess.ROLE_VIEWER:
            can_control = False

        generated_password = None
        existing_by_email = User.objects.filter(email=email).first()
        existing_by_username = User.objects.filter(username=username).first() if username else None
        if existing_by_email and existing_by_username and existing_by_email.pk != existing_by_username.pk:
            messages.error(request, "Email and username refer to different existing users.")
            return redirect("dashboard:onboard-client", pk=pk)

        user = existing_by_email or existing_by_username
        creating_new_user = user is None

        if user and (user.is_staff or user.is_superuser):
            messages.error(request, "Operator accounts cannot be linked as mobile clients.")
            return redirect("dashboard:onboard-client", pk=pk)

        if creating_new_user:
            if not username:
                messages.error(request, "Username is required for a new client account.")
                return redirect("dashboard:onboard-client", pk=pk)
            validation_user = password_validation_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            if not password:
                generated_password = generate_compliant_password(user=validation_user)
                password = generated_password
            else:
                try:
                    validate_console_password(password, user=validation_user)
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return redirect("dashboard:onboard-client", pk=pk)
        elif CustomerSiteAccess.objects.filter(user=user, site=site).exists():
            messages.info(request, f"'{user.username}' already has access to {site.name}.")
            return redirect("dashboard:onboard-client", pk=pk)

        try:
            with transaction.atomic():
                if creating_new_user:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                else:
                    profile_updates = []
                    if first_name and not user.first_name:
                        user.first_name = first_name
                        profile_updates.append("first_name")
                    if last_name and not user.last_name:
                        user.last_name = last_name
                        profile_updates.append("last_name")
                    if profile_updates:
                        user.save(update_fields=profile_updates)

                profile, _ = CustomerProfile.objects.get_or_create(user=user)
                if phone:
                    profile.phone_number = phone
                profile.is_mobile_user = True
                profile.save(update_fields=["phone_number", "is_mobile_user", "updated_at"])

                CustomerSiteAccess.objects.create(
                    user=user,
                    site=site,
                    role=role,
                    can_control_alarm=can_control,
                )

                pkg = SubscriptionPackage.objects.filter(pk=package_id).first() if package_id else None
                if monthly_rate or next_due_date:
                    if Subscription.objects.filter(site=site).exists():
                        messages.info(request, f"'{site.name}' already has a billing plan, so onboarding only linked access.")
                    else:
                        parsed_rate = parse_decimal_field(
                            monthly_rate,
                            label="Monthly rate",
                            min_value=Decimal("0.00"),
                        )
                        parsed_due_date = parse_date_field(next_due_date, label="First due date")
                        parsed_billing_day = (
                            parse_int_field(
                                billing_day,
                                label="Billing day",
                                min_value=1,
                                max_value=28,
                            )
                            if billing_day
                            else billing_day_from_due_date(parsed_due_date)
                        )
                        parsed_grace_days = parse_int_field(
                            grace_period_days or "7",
                            label="Grace period",
                            min_value=0,
                            max_value=30,
                        )
                        status = Subscription.classify_status(
                            next_due_date=parsed_due_date,
                            grace_period_days=parsed_grace_days,
                        )
                        Subscription.objects.create(
                            site=site,
                            monthly_rate=parsed_rate,
                            billing_day=parsed_billing_day,
                            next_due_date=parsed_due_date,
                            grace_period_days=parsed_grace_days,
                            status=status,
                            suspended_at=timezone.now() if status == Subscription.STATUS_SUSPENDED else None,
                            package=pkg,
                        )

            # Send welcome email if possible
            if user.email:
                send_welcome_email(user, site, generated_password if creating_new_user else None)

            if creating_new_user and generated_password:
                messages.success(
                    request,
                    f"Client '{username}' {'added' if access_management_mode else 'onboarded'} successfully. "
                    "Save the security credentials below—they won't be shown again.",
                )
            elif creating_new_user:
                messages.success(request, f"Client '{username}' {'added' if access_management_mode else 'onboarded'} successfully.")
            else:
                messages.success(request, f"Existing client '{user.username}' linked to {site.name}.")

            # SUCCESS STATE: Instead of redirecting immediately, render the victory screen
            return render(request, self.template_name, {
                "site": site,
                "provision_success": True,
                "access_management_mode": access_management_mode,
                "client_username": user.username,
                "client_password": generated_password if creating_new_user else "",
                "client_email": user.email,
            })

        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:onboard-client", pk=pk)
        except Exception as e:
            messages.error(request, f"Onboarding failed: {e}")
            return redirect("dashboard:onboard-client", pk=pk)


class SiteAccessUpdateView(StaffRequiredMixin, View):
    def post(self, request, pk, access_id):

        site = get_object_or_404(Site, pk=pk)
        access = get_object_or_404(CustomerSiteAccess, pk=access_id, site=site)
        role = request.POST.get("role", "").strip()
        can_control = request.POST.get("can_control_alarm") == "on"

        valid_roles = {
            CustomerSiteAccess.ROLE_OWNER,
            CustomerSiteAccess.ROLE_MANAGER,
            CustomerSiteAccess.ROLE_VIEWER,
        }
        if role not in valid_roles:
            messages.error(request, "Please choose a valid access role.")
            return redirect("dashboard:onboard-client", pk=pk)
        if role == CustomerSiteAccess.ROLE_VIEWER:
            can_control = False

        access.role = role
        access.can_control_alarm = can_control
        access.save(update_fields=["role", "can_control_alarm"])
        messages.success(request, f"Updated access for '{access.user.username}'.")
        return redirect("dashboard:onboard-client", pk=pk)


class SiteAccessDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk, access_id):

        site = get_object_or_404(Site, pk=pk)
        access = get_object_or_404(CustomerSiteAccess, pk=access_id, site=site)
        username = access.user.username
        access.delete()
        messages.success(request, f"Removed '{username}' from {site.name}.")
        return redirect("dashboard:onboard-client", pk=pk)


class EventPicturesView(StaffRequiredMixin, View):
    """
    Return resolved picture URLs for an alarm event as JSON.
    Uses Django session auth so the console can fetch without JWT.
    """

    def get(self, request, pk, event_id):
        from apps.alarms.models import AlarmEvent
        from django.http import JsonResponse

        site = get_object_or_404(Site, pk=pk)
        event = get_object_or_404(AlarmEvent, id=event_id, site=site)

        stored_pictures = collect_related_event_media(event)
        if not stored_pictures:
            return JsonResponse({"pictures": [], "error": "No pictures found for this event."})

        service = HikPartnerService()
        resolved = []
        for pic in stored_pictures:
            url = pic.get("url", "")
            media_id = pic.get("id", "")
            alarm_data = pic.get("alarm_data") or {}
            try:
                if pic.get("needs_url_fetch") or url.startswith("ISAPI_FILES"):
                    result = service.get_alarm_picture_url(url)
                    real_url = result.get("pictureUrl", "")
                    media_type = resolve_picture_media_type(
                        url=real_url,
                        media_id=media_id,
                        stored_type=pic.get("type", ""),
                        alarm_data=alarm_data,
                        probe_remote=True,
                    )
                    resolved.append({
                        "id": media_id,
                        "url": real_url,
                        "encrypt": result.get("encrypt", False),
                        "type": media_type,
                    })
                else:
                    media_type = resolve_picture_media_type(
                        url=url,
                        media_id=media_id,
                        stored_type=pic.get("type", ""),
                        alarm_data=alarm_data,
                        probe_remote=True,
                    )
                    resolved.append({
                        "id": media_id,
                        "url": url,
                        "encrypt": "isEncrypted=1" in url,
                        "type": media_type,
                    })
            except Exception as exc:
                resolved.append({"id": pic.get("id", ""), "url": None, "error": str(exc)})

        return JsonResponse({
            "pictures": resolved,
            "event_type": event.event_type,
            "zone_name": event.payload.get("alarmData", {}).get("CIDEvent", {}).get("zoneName"),
            "subsystem_name": event.payload.get("alarmData", {}).get("subSysNo"),
        })

def send_welcome_email(user, site, temp_password=None):
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings as conf

    app_links = getattr(conf, "SECUREHUB_APP_LINKS", {})
    recipient_name = user.get_full_name() or user.username

    body_lines = [
        f"Hi {recipient_name},",
        "",
        f"Welcome to SecureHub. Your access for '{site.name}' is ready.",
        "",
        f"Username: {user.username}",
    ]
    if temp_password:
        body_lines.extend(
            [
                "A temporary password has been created for your account.",
                "For security, SecureHub does not send passwords by email.",
                "Your installer or operator should share it with you separately.",
            ]
        )
    else:
        body_lines.extend(
            [
                "Use your existing password to sign in.",
            ]
        )

    download_lines = []
    if app_links.get("android"):
        download_lines.append(f"Android app: {app_links['android']}")
    if app_links.get("ios"):
        download_lines.append(f"iPhone app: {app_links['ios']}")
    if app_links.get("web"):
        download_lines.append(f"Web portal: {app_links['web']}")

    if download_lines:
        body_lines.extend(["", "Get started with SecureHub:", *download_lines])

    if app_links.get("support"):
        body_lines.extend(["", f"Support: {app_links['support']}"])

    body_lines.extend(["", "— SecureHub Support"])

    html_parts = [
        f"<p>Hi {recipient_name},</p>",
        f"<p>Welcome to <strong>SecureHub</strong>. Your access for <strong>{site.name}</strong> is ready.</p>",
        "<div style=\"padding:16px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc;\">",
        f"<p style=\"margin:0 0 8px 0;\"><strong>Username:</strong> {user.username}</p>",
    ]
    if temp_password:
        html_parts.append("<p style=\"margin:0 0 8px 0;\"><strong>A temporary password has been created for your account.</strong></p>")
        html_parts.append("<p style=\"margin:0;color:#475569;\">For security, SecureHub does not send passwords by email. Your installer or operator should share it with you separately.</p>")
    else:
        html_parts.append("<p style=\"margin:0;color:#475569;\">Use your existing password to sign in.</p>")
    html_parts.append("</div>")

    link_chips = []
    if app_links.get("android"):
        link_chips.append(f'<a href="{app_links["android"]}" style="display:inline-block;margin:0 8px 8px 0;padding:10px 14px;background:#0f172a;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">Android App</a>')
    if app_links.get("ios"):
        link_chips.append(f'<a href="{app_links["ios"]}" style="display:inline-block;margin:0 8px 8px 0;padding:10px 14px;background:#0f172a;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">iPhone App</a>')
    if app_links.get("web"):
        link_chips.append(f'<a href="{app_links["web"]}" style="display:inline-block;margin:0 8px 8px 0;padding:10px 14px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">Web Portal</a>')
    if link_chips:
        html_parts.append("<p style=\"margin:16px 0 8px 0;\"><strong>Get started:</strong></p>")
        html_parts.append(f"<div>{''.join(link_chips)}</div>")
    if app_links.get("support"):
        html_parts.append(f'<p style="margin-top:16px;">Support: <a href="{app_links["support"]}">{app_links["support"]}</a></p>')
    html_parts.append("<p>SecureHub Support</p>")

    try:
        message = EmailMultiAlternatives(
            subject=f"[SecureHub] Your account for {site.name}",
            body="\n".join(body_lines),
            from_email=conf.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative("".join(html_parts), "text/html")
        message.send(fail_silently=True)
    except Exception:
        pass
