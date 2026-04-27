from datetime import date, timedelta
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.generic import ListView, TemplateView, View

from apps.alarms.event_labels import humanize_event_label
from apps.alarms.media import collect_related_event_media, resolve_picture_media_type
from apps.alarms.models import AlarmEvent as Event
from apps.alarms.tasks import (
    initial_site_discovery,
    refresh_hik_site_health,
    send_reactivation_notice,
    send_subscription_lockout_notice,
    send_suspension_notice,
    sync_hik_alarm_status,
    sync_hik_site_devices,
)
from apps.hik_adapter.services import HikPartnerService
from apps.sites.models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, CustomerSiteAccess, Site, Subsystem, Subscription, SubscriptionPackage, SubscriptionPayment, Zone
from apps.sites.scenes import SCENE_OPTIONS, normalize_scene_label
from apps.accounts.models import CustomerGroup, FCMDevice
from apps.communication.models import BroadcastMessage
from apps.communication.tasks import send_broadcast_push_notifications
from apps.dashboard.event_presenters import serialize_console_event, should_hide_console_event


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return bool(self.request.user.is_authenticated and self.request.user.is_staff)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={self.request.get_full_path()}"
            return redirect(login_url)
        return HttpResponseForbidden("Staff access required.")


def _visible_console_events(site: Site, *, limit: int = 15) -> list[Event]:
    # Pull a slightly wider slice so we can suppress duplicate snapshot rows
    # without starving the compact feed.
    candidates = list(
        Event.objects.filter(site=site)
        .select_related("site", "subsystem", "zone")
        .order_by("-occurred_at")[: limit * 3]
    )
    visible = [event for event in candidates if not should_hide_console_event(event)]
    return visible[:limit]


def _fault_age_label(timestamp):
    if not timestamp:
        return "current"
    return f"{timesince(timestamp, timezone.now())} ago"


def _is_problem_status(value) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return normalized not in {"ok", "normal", "online", "available", "good", "none", "unknown"}


def _build_active_faults(site: Site, *, limit: int | None = None) -> list[dict]:
    """
    Build current active faults from the latest device/zone health state.

    Historical alarm events remain in the event feed. The active-fault banner
    should only show things that are still true in the local status snapshot.
    """
    faults = []

    def add_fault(*, item_id, label, source, detail="", severity="critical", timestamp=None):
        faults.append(
            {
                "id": item_id,
                "label": label,
                "source": source,
                "detail": detail,
                "severity": severity,
                "age": _fault_age_label(timestamp),
                "_sort_at": timestamp or timezone.now(),
            }
        )

    devices = site.devices.prefetch_related("subsystems__zones", "peripherals", "outputs")
    for device in devices:
        device_seen_at = device.last_seen_at or device.last_health_check or device.updated_at
        if not device.is_online:
            add_fault(
                item_id=f"panel:{device.id}:offline",
                label="Panel Offline",
                source=device.name,
                detail=device.serial_number,
                timestamp=device_seen_at,
            )
        if device.normalized_battery_status == AlarmPanelDevice.BATTERY_LOW:
            add_fault(
                item_id=f"panel:{device.id}:battery",
                label="Panel Battery Low",
                source=device.name,
                detail=device.power_status_label,
                severity="high",
                timestamp=device.updated_at,
            )
        if str(device.work_status or "").strip().lower() == AlarmPanelDevice.WORK_ALARM:
            add_fault(
                item_id=f"panel:{device.id}:alarm",
                label="Panel In Alarm",
                source=device.name,
                detail=device.work_status,
                timestamp=device.updated_at,
            )

        for subsystem in device.subsystems.all():
            for zone in subsystem.zones.all():
                zone_seen_at = zone.last_seen_at or zone.updated_at
                if zone.state == Zone.STATE_ALARM:
                    add_fault(
                        item_id=f"zone:{zone.id}:alarm",
                        label="Zone Alarm",
                        source=zone.name,
                        detail=subsystem.name,
                        timestamp=zone_seen_at,
                    )
                elif zone.state == Zone.STATE_OPEN and subsystem.status != Subsystem.STATUS_DISARMED:
                    add_fault(
                        item_id=f"zone:{zone.id}:open",
                        label="Zone Open",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone_seen_at,
                    )
                if not zone.is_online:
                    add_fault(
                        item_id=f"zone:{zone.id}:offline",
                        label="Sensor Offline",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone_seen_at,
                    )
                if zone.low_battery:
                    add_fault(
                        item_id=f"zone:{zone.id}:battery",
                        label="Sensor Battery Low",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone.updated_at,
                    )
                if zone.tamper:
                    add_fault(
                        item_id=f"zone:{zone.id}:tamper",
                        label="Sensor Tamper",
                        source=zone.name,
                        detail=subsystem.name,
                        timestamp=zone.updated_at,
                    )
                if zone.shielded:
                    add_fault(
                        item_id=f"zone:{zone.id}:shielded",
                        label="Sensor Shielded",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone.updated_at,
                    )

        for peripheral in device.peripherals.all():
            source = peripheral.name
            timestamp = peripheral.updated_at
            if not peripheral.is_online:
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:offline",
                    label="Peripheral Offline",
                    source=source,
                    detail=peripheral.peripheral_type_label or peripheral.peripheral_type,
                    severity="high",
                    timestamp=timestamp,
                )
            if _is_problem_status(peripheral.battery_status):
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:battery",
                    label="Peripheral Battery Issue",
                    source=source,
                    detail=peripheral.battery_status,
                    severity="high",
                    timestamp=timestamp,
                )
            if peripheral.tamper:
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:tamper",
                    label="Peripheral Tamper",
                    source=source,
                    detail=peripheral.peripheral_type_label or peripheral.peripheral_type,
                    timestamp=timestamp,
                )

        for output in device.outputs.all():
            if output.status == AlarmOutput.STATUS_NOT_RELATED or not output.is_available:
                continue
            source = output.name
            timestamp = output.updated_at
            if not output.is_online:
                add_fault(
                    item_id=f"output:{output.id}:offline",
                    label="Output Offline",
                    source=source,
                    detail=output.serial_number,
                    severity="high",
                    timestamp=timestamp,
                )
            if output.tamper:
                add_fault(
                    item_id=f"output:{output.id}:tamper",
                    label="Output Tamper",
                    source=source,
                    detail=output.access_module_type or "output module",
                    timestamp=timestamp,
                )
            if _is_problem_status(output.battery_status):
                add_fault(
                    item_id=f"output:{output.id}:battery",
                    label="Output Battery Issue",
                    source=source,
                    detail=output.battery_status,
                    severity="high",
                    timestamp=timestamp,
                )

    faults.sort(key=lambda item: item["_sort_at"], reverse=True)
    for fault in faults:
        fault.pop("_sort_at", None)
    if limit is not None:
        return faults[:limit]
    return faults


CONSOLE_LOGIN_ATTEMPT_LIMIT = 5
CONSOLE_LOGIN_LOCKOUT_SECONDS = 300


def _parse_decimal_field(raw_value, *, label, min_value=None):
    try:
        value = Decimal(str(raw_value).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{label} must be a valid number.")
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} must be at least {min_value}.")
    return value


def _parse_int_field(raw_value, *, label, min_value=None, max_value=None):
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f"{label} must be a whole number.")
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} must be at least {min_value}.")
    if max_value is not None and value > max_value:
        raise ValueError(f"{label} must be at most {max_value}.")
    return value


def _parse_date_field(raw_value, *, label):
    try:
        return date.fromisoformat(str(raw_value).strip())
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f"{label} must be a valid date.")


def _validate_subscription_payment_window(subscription, *, period_start, period_end, exclude_payment_id=None):
    overlapping_payments = subscription.payments.filter(
        period_start__lte=period_end,
        period_end__gte=period_start,
    )
    if exclude_payment_id is not None:
        overlapping_payments = overlapping_payments.exclude(pk=exclude_payment_id)

    if overlapping_payments.exists():
        raise ValueError("Payment periods cannot overlap existing records for this site.")


def _validate_reactivation_due_date(subscription, due_date):
    next_status = Subscription.classify_status(
        next_due_date=due_date,
        grace_period_days=subscription.grace_period_days,
    )
    if next_status != Subscription.STATUS_ACTIVE:
        raise ValueError("Reactivation requires a next due date that is today or in the future.")


def _billing_day_from_due_date(due_date):
    return min(due_date.day, 28)


def _parse_payment_method(raw_value):
    value = str(raw_value or "").strip()
    if not value:
        return ""
    valid_methods = {choice[0] for choice in SubscriptionPayment.METHOD_CHOICES}
    if value not in valid_methods:
        raise ValueError("Please choose a valid payment method.")
    return value


def _request_client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR", "unknown")


def _console_login_cache_keys(request, username: str) -> tuple[str, str]:
    client_ip = _request_client_ip(request)
    username_value = username.strip().lower() or "unknown"
    return (
        f"console-login:ip:{client_ip}",
        f"console-login:user:{client_ip}:{username_value}",
    )


def _console_login_locked(request, username: str) -> bool:
    return any(
        (cache.get(key) or 0) >= CONSOLE_LOGIN_ATTEMPT_LIMIT
        for key in _console_login_cache_keys(request, username)
    )


def _record_console_login_failure(request, username: str) -> None:
    for key in _console_login_cache_keys(request, username):
        attempts = (cache.get(key) or 0) + 1
        cache.set(key, attempts, timeout=CONSOLE_LOGIN_LOCKOUT_SECONDS)


def _clear_console_login_failures(request, username: str) -> None:
    for key in _console_login_cache_keys(request, username):
        cache.delete(key)


def _password_validation_user(*, username: str, email: str, first_name: str = "", last_name: str = "", user_id=None):
    return User(
        pk=user_id,
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )


def _validate_console_password(password: str, *, user: User) -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValueError(" ".join(exc.messages)) from exc


def _generate_compliant_password(*, user: User) -> str:
    import secrets

    for _ in range(10):
        candidate = secrets.token_urlsafe(16)
        try:
            _validate_console_password(candidate, user=user)
            return candidate
        except ValueError:
            continue
    raise ValueError("Unable to generate a compliant temporary password. Please provide one manually.")


def _build_display_alarm_peripherals(site: Site):
    actual_peripherals = list(
        AlarmPeripheral.objects.filter(site=site)
        .select_related("device")
        .order_by("peripheral_type", "peripheral_number")
    )
    display_peripherals = []

    for peripheral in actual_peripherals:
        display_peripherals.append(
            {
                "id": str(peripheral.id),
                "name": peripheral.name,
                "display_type": peripheral.get_peripheral_type_display(),
                "serial_number": peripheral.serial_number,
                "is_online": peripheral.is_online,
                "battery_status": peripheral.battery_status,
                "signal_strength": peripheral.signal_strength,
                "network_status": peripheral.network_status,
                "tamper": peripheral.tamper,
                "peripheral_type": peripheral.peripheral_type,
                "peripheral_number": peripheral.peripheral_number,
                "source": "hik",
            }
        )

    display_peripherals.sort(key=lambda item: (item["peripheral_type"], item["peripheral_number"], item["name"]))
    return display_peripherals


def _filter_installed_module_peripherals(display_peripherals: list[dict]) -> list[dict]:
    module_types = {
        AlarmPeripheral.TYPE_OUTPUT_MODULE,
        AlarmPeripheral.TYPE_REPEATER,
        AlarmPeripheral.TYPE_SIREN,
        AlarmPeripheral.TYPE_TRANSMITTER,
    }
    return [
        item
        for item in display_peripherals
        if item["peripheral_type"] in module_types
    ]


def _filter_installed_alarm_outputs(site: Site):
    return (
        AlarmOutput.objects.filter(site=site)
        .exclude(status=AlarmOutput.STATUS_NOT_RELATED)
        .select_related("device")
        .order_by("output_number")
    )


def _compute_alarm_inventory_counts(site: Site, display_peripherals: list[dict]) -> dict:
    peripheral_counts = {}
    for item in display_peripherals:
        peripheral_counts[item["peripheral_type"]] = peripheral_counts.get(item["peripheral_type"], 0) + 1
    installed_outputs_count = _filter_installed_alarm_outputs(site).count()

    return {
        "zones": Zone.objects.filter(subsystem__site=site, device_type=Zone.DEVICE_TYPE_ZONE).count(),
        "keypads": peripheral_counts.get(AlarmPeripheral.TYPE_KEYPAD, 0),
        "keyfobs": peripheral_counts.get(AlarmPeripheral.TYPE_KEYFOB, 0),
        "card_readers": peripheral_counts.get(AlarmPeripheral.TYPE_CARD_READER, 0),
        "sirens": peripheral_counts.get(AlarmPeripheral.TYPE_SIREN, 0),
        "repeaters": peripheral_counts.get(AlarmPeripheral.TYPE_REPEATER, 0),
        "transmitters": peripheral_counts.get(AlarmPeripheral.TYPE_TRANSMITTER, 0),
        "output_modules": peripheral_counts.get(AlarmPeripheral.TYPE_OUTPUT_MODULE, 0),
        "outputs": installed_outputs_count,
    }

class ConsoleLoginView(View):
    template_name = "dashboard/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return render(request, self.template_name, {"next": request.GET.get("next", "/console/")})

    def post(self, request):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next", "/console/")
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/console/"
        if _console_login_locked(request, username):
            return render(request, self.template_name, {
                "error": "Too many sign-in attempts. Please wait a few minutes and try again.",
                "next": next_url,
            })
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            _clear_console_login_failures(request, username)
            login(request, user)
            return redirect(next_url)
        _record_console_login_failure(request, username)
        return render(request, self.template_name, {
            "error": "Invalid credentials or insufficient permissions.",
            "next": next_url,
        })


class DashboardHomeView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites_qs = Site.objects.select_related("subscription").prefetch_related("access_list")
        total_sites = sites_qs.count()
        total_panels = AlarmPanelDevice.objects.count()
        online_devices = AlarmPanelDevice.objects.filter(is_online=True).count()
        recent_events = Event.objects.select_related("site", "subsystem", "zone").order_by("-occurred_at")[:10]
        context["total_sites"] = total_sites
        context["total_alarms"] = total_panels
        context["online_devices"] = online_devices
        context["recent_events"] = recent_events
        context["recent_events_payload"] = [serialize_console_event(event) for event in recent_events]
        context["pending_onboarding_sites"] = sites_qs.filter(access_list__isnull=True).distinct().count()
        context["pending_billing_sites"] = sites_qs.filter(subscription__isnull=True).count()
        context["ready_sites"] = sites_qs.filter(
            access_list__isnull=False,
            subscription__isnull=False,
            is_active=True,
        ).distinct().count()

        # Analytics: Events distribution last 24h
        now = timezone.now()
        start_time = now - timedelta(hours=24)
        events_24h = Event.objects.filter(occurred_at__gte=start_time)

        total_events_24h = events_24h.count()
        critical_events_24h = events_24h.filter(severity=Event.SEVERITY_CRITICAL).count()
        high_events_24h = events_24h.filter(severity=Event.SEVERITY_HIGH).count()
        alarm_events_24h = events_24h.filter(event_category=Event.CATEGORY_ALARM).count()
        health_events_24h = events_24h.filter(event_category=Event.CATEGORY_HEALTH).count()
        arm_events_24h = events_24h.filter(event_category=Event.CATEGORY_ARM).count()
        system_events_24h = events_24h.filter(event_category=Event.CATEGORY_SYSTEM).count()

        # Group by hour
        hourly_data = [0] * 25
        labels = []
        peak_hour_label = labels[0] if labels else ""
        peak_hour_count = 0
        for i in range(25):
            h_time = start_time + timedelta(hours=i)
            hour_label = h_time.strftime("%H:00")
            labels.append(hour_label)
            count = events_24h.filter(
                occurred_at__gte=h_time,
                occurred_at__lt=h_time + timedelta(hours=1)
            ).count()
            hourly_data[i] = count
            if count >= peak_hour_count:
                peak_hour_count = count
                peak_hour_label = hour_label

        event_mix_labels = ["Alarm", "Health", "Arm / Disarm", "System"]
        event_mix_data = [
            alarm_events_24h,
            health_events_24h,
            arm_events_24h,
            system_events_24h,
        ]

        connected_ratio = round((online_devices / total_panels) * 100) if total_panels else 0
        readiness_ratio = round((context["ready_sites"] / total_sites) * 100) if total_sites else 0

        context["chart_labels"] = json.dumps(labels)
        context["chart_data"] = json.dumps(hourly_data)
        context["event_mix_labels"] = json.dumps(event_mix_labels)
        context["event_mix_data"] = json.dumps(event_mix_data)
        context["events_24h_total"] = total_events_24h
        context["critical_events_24h"] = critical_events_24h
        context["high_events_24h"] = high_events_24h
        context["alarm_events_24h"] = alarm_events_24h
        context["health_events_24h"] = health_events_24h
        context["arm_events_24h"] = arm_events_24h
        context["system_events_24h"] = system_events_24h
        context["peak_hour_label"] = peak_hour_label
        context["peak_hour_count"] = peak_hour_count
        context["connected_ratio"] = connected_ratio
        context["readiness_ratio"] = readiness_ratio

        # Yesterday comparison for event delta
        yesterday_start = start_time - timedelta(hours=24)
        events_yesterday = Event.objects.filter(
            occurred_at__gte=yesterday_start,
            occurred_at__lt=start_time,
        ).count()
        events_delta = total_events_24h - events_yesterday
        context["events_delta"] = events_delta
        context["abs_events_delta"] = abs(events_delta)

        # Top 5 sites by 24h activity
        top_sites_raw = list(
            Event.objects.filter(occurred_at__gte=start_time)
            .values("site__name", "site__id")
            .annotate(event_count=Count("id"))
            .order_by("-event_count")[:5]
        )
        if top_sites_raw:
            max_count = max(item["event_count"] for item in top_sites_raw) or 1
            context["top_sites_events"] = [
                {
                    "name": item["site__name"] or "Unknown",
                    "id": str(item["site__id"]),
                    "count": item["event_count"],
                    "pct": int((item["event_count"] / max_count) * 100),
                }
                for item in top_sites_raw
            ]
        else:
            context["top_sites_events"] = []

        context["overdue_mrr"] = (
            Subscription.objects.filter(status=Subscription.STATUS_OVERDUE)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["suspended_mrr"] = (
            Subscription.objects.filter(status=Subscription.STATUS_SUSPENDED)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )

        return context

class SiteDirectoryView(StaffRequiredMixin, ListView):
    model = Site
    template_name = "dashboard/sites.html"
    context_object_name = "sites"

    def get_queryset(self):
        qs = super().get_queryset().select_related("subscription").prefetch_related("devices", "access_list")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(hik_site_id__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scene_options"] = SCENE_OPTIONS
        all_sites_qs = Site.objects.select_related("subscription")
        total = all_sites_qs.count()
        count_no_plan = all_sites_qs.filter(subscription__isnull=True).count()
        online_site_ids = set(
            AlarmPanelDevice.objects.filter(is_online=True).values_list("site_id", flat=True)
        )
        context["total_sites_count"] = total
        context["count_no_plan"] = count_no_plan
        context["count_with_plan"] = total - count_no_plan
        context["count_online"] = len(online_site_ids)
        context["current_query"] = self.request.GET.get("q", "")
        return context

class SiteMapView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/site_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites = Site.objects.all().prefetch_related("devices")
        service = HikPartnerService()
        
        sites_data = []
        for site in sites:
            if site.latitude is None or site.longitude is None:
                if site.address or site.city or site.state:
                    service.geocode_site_location(site)

            if site.latitude is None or site.longitude is None:
                continue

            if site.latitude and site.longitude:
                # Determine connectivity and gather panel metadata
                devices = []
                is_any_online = False
                for d in site.devices.all():
                    if d.is_online: 
                        is_any_online = True
                    devices.append({
                        "name": d.name,
                        "model": d.model_number,
                        "firmware": d.firmware_version,
                        "is_online": d.is_online
                    })
                
                sites_data.append({
                    "id": str(site.id),
                    "name": site.name,
                    "address": site.address,
                    "city": site.city,
                    "state": site.state,
                    "primary_industry": normalize_scene_label(site.primary_industry),
                    "secondary_industry": site.secondary_industry,
                    "sub_status": getattr(site, 'subscription', None).status if hasattr(site, 'subscription') else "active",
                    "hik_id": site.hik_site_id,
                    "lat": float(site.latitude),
                    "lng": float(site.longitude),
                    "is_active": site.is_active,
                    "is_online": is_any_online,
                    "devices": devices,
                    "url": f"/console/sites/{site.id}/"
                })
        
        context["sites_json"] = json.dumps(sites_data)
        return context

class SiteConsoleView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/site_console.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = get_object_or_404(Site, pk=self.kwargs["pk"])
        service = HikPartnerService()
        context["site"] = site
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
            panic_capability = service.get_site_panic_capability(site)
            cache.set(f"site-panic-capability:{site.id}", panic_capability, timeout=60)
        context["panic_capability"] = panic_capability
        display_alarm_peripherals = _build_display_alarm_peripherals(site)
        context["alarm_peripherals"] = display_alarm_peripherals
        context["alarm_module_peripherals"] = _filter_installed_module_peripherals(display_alarm_peripherals)
        context["alarm_outputs"] = _filter_installed_alarm_outputs(site)
        context["inventory_counts"] = _compute_alarm_inventory_counts(site, display_alarm_peripherals)
        recent_events = _visible_console_events(site, limit=15)
        context["recent_events"] = recent_events
        context["recent_events_payload"] = [serialize_console_event(event) for event in recent_events]
        active_faults = _build_active_faults(site)
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

class WebhookLogsView(StaffRequiredMixin, ListView):
    model = Event
    template_name = "dashboard/logs.html"
    context_object_name = "events"
    paginate_by = 30
    ordering = ["-occurred_at"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("site")
        site_id = self.request.GET.get("site")
        event_type = self.request.GET.get("type")
        
        if site_id:
            qs = qs.filter(site_id=site_id)
        if event_type:
            valid_categories = {
                Event.CATEGORY_ALARM,
                Event.CATEGORY_ARM,
                Event.CATEGORY_SYSTEM,
                Event.CATEGORY_HEALTH,
                Event.CATEGORY_INFO,
            }
            if event_type in valid_categories:
                qs = qs.filter(event_category=event_type)
                
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sites"] = Site.objects.all()
        context["current_site"] = self.request.GET.get("site", "")
        context["current_type"] = self.request.GET.get("type", "")
        qs = self.get_queryset()
        context["count_critical"] = qs.filter(severity=Event.SEVERITY_CRITICAL).count()
        context["count_high"] = qs.filter(severity=Event.SEVERITY_HIGH).count()
        context["count_alarm"] = qs.filter(event_category=Event.CATEGORY_ALARM).count()
        context["count_arm"] = qs.filter(event_category=Event.CATEGORY_ARM).count()
        return context

class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = "dashboard/users.html"
    context_object_name = "users"
    ordering = ["-is_superuser", "username"]

    def get_queryset(self):
        return User.objects.filter(is_staff=True).order_by("-is_superuser", "username")


class CustomerDirectoryView(StaffRequiredMixin, ListView):
    model = User
    template_name = "dashboard/customers.html"
    context_object_name = "customers"

    def get_queryset(self):
        qs = (
            User.objects.filter(is_staff=False)
            .select_related("customer_profile__group")
            .prefetch_related("customersiteaccess_set__site", "fcm_devices")
            .order_by("username")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sites"] = Site.objects.order_by("name")
        context["groups"] = CustomerGroup.objects.all()
        context["current_query"] = self.request.GET.get("q", "").strip()
        all_customers = User.objects.filter(is_staff=False)
        context["count_all_customers"] = all_customers.count()
        context["count_active_customers"] = all_customers.filter(is_active=True).count()
        context["count_no_access"] = all_customers.filter(customersiteaccess__isnull=True).count()
        return context


class StaffUserCreateView(StaffRequiredMixin, View):
    def post(self, request):
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        is_superuser = request.POST.get("is_superuser") == "on"

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required.")
            return redirect("dashboard:user-list")
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("dashboard:user-list")
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect("dashboard:user-list")
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already in use.")
            return redirect("dashboard:user-list")
        try:
            _validate_console_password(
                password,
                user=_password_validation_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:user-list")

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=is_superuser,
        )
        messages.success(request, f"Staff user '{username}' created.")
        return redirect("dashboard:user-list")


class StaffUserUpdateView(StaffRequiredMixin, View):
    def post(self, request, user_id):
        staff_user = get_object_or_404(User, pk=user_id, is_staff=True)
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        is_superuser = request.POST.get("is_superuser") == "on"
        is_active = request.POST.get("is_active") == "on"

        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect("dashboard:user-list")
        if User.objects.exclude(pk=staff_user.pk).filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect("dashboard:user-list")
        if User.objects.exclude(pk=staff_user.pk).filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already in use.")
            return redirect("dashboard:user-list")
        if request.user.pk == staff_user.pk and not is_active:
            messages.error(request, "You cannot deactivate your own operator account.")
            return redirect("dashboard:user-list")

        staff_user.username = username
        staff_user.email = email
        staff_user.first_name = first_name
        staff_user.last_name = last_name
        staff_user.is_staff = True
        staff_user.is_superuser = is_superuser
        staff_user.is_active = is_active
        if password:
            try:
                _validate_console_password(
                    password,
                    user=_password_validation_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        user_id=staff_user.pk,
                    ),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("dashboard:user-list")
            staff_user.set_password(password)
        staff_user.save()
        messages.success(request, f"Staff user '{staff_user.username}' updated.")
        return redirect("dashboard:user-list")


class StaffUserDeleteView(StaffRequiredMixin, View):
    def post(self, request, user_id):
        staff_user = get_object_or_404(User, pk=user_id, is_staff=True)
        if request.user.pk == staff_user.pk:
            messages.error(request, "You cannot delete your own operator account.")
            return redirect("dashboard:user-list")
        username = staff_user.username
        staff_user.delete()
        messages.success(request, f"Staff user '{username}' deleted.")
        return redirect("dashboard:user-list")


class CustomerUserCreateView(StaffRequiredMixin, View):
    def post(self, request):
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()
        site_id = request.POST.get("site_id", "").strip()
        role = request.POST.get("role", "").strip() or "owner"
        can_control = request.POST.get("can_control_alarm") == "on"

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required.")
            return redirect("dashboard:customer-list")
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("dashboard:customer-list")
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect("dashboard:customer-list")
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already in use.")
            return redirect("dashboard:customer-list")
        try:
            _validate_console_password(
                password,
                user=_password_validation_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:customer-list")

        valid_roles = {"owner", "manager", "viewer"}
        if role not in valid_roles:
            messages.error(request, "Please choose a valid customer role.")
            return redirect("dashboard:customer-list")
        if role == "viewer":
            can_control = False

        group_id = request.POST.get("group_id", "").strip()
        group = CustomerGroup.objects.filter(pk=group_id).first() if group_id else None

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            profile = user.customer_profile
            profile.phone_number = phone
            profile.is_mobile_user = True
            profile.group = group
            profile.save(update_fields=["phone_number", "is_mobile_user", "group", "updated_at"])

            if site_id:
                site = get_object_or_404(Site, pk=site_id)
                CustomerSiteAccess.objects.create(
                    user=user,
                    site=site,
                    role=role,
                    can_control_alarm=can_control,
                )

        messages.success(request, f"Customer '{username}' created.")
        return redirect("dashboard:customer-list")


class CustomerUserUpdateView(StaffRequiredMixin, View):
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id, is_staff=False)
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect("dashboard:customer-list")
        if User.objects.exclude(pk=user.pk).filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect("dashboard:customer-list")
        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already in use.")
            return redirect("dashboard:customer-list")

        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = is_active
        if password:
            try:
                _validate_console_password(
                    password,
                    user=_password_validation_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        user_id=user.pk,
                    ),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("dashboard:customer-list")
            user.set_password(password)
        user.save()

        group_id = request.POST.get("group_id", "").strip()
        group = CustomerGroup.objects.filter(pk=group_id).first() if group_id else None

        profile = user.customer_profile
        profile.phone_number = phone
        profile.group = group
        profile.save(update_fields=["phone_number", "group", "updated_at"])

        messages.success(request, f"Customer '{user.username}' updated.")
        return redirect("dashboard:customer-list")


class CustomerUserDeleteView(StaffRequiredMixin, View):
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id, is_staff=False)
        username = user.username
        user.delete()
        messages.success(request, f"Customer '{username}' deleted.")
        return redirect("dashboard:customer-list")


class CustomerGroupListView(StaffRequiredMixin, View):
    template_name = "dashboard/groups.html"

    def get(self, request):
        groups = CustomerGroup.objects.annotate(member_count=Count("members"))
        return render(request, self.template_name, {"groups": groups})

    def post(self, request):
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6366f1").strip()
        description = request.POST.get("description", "").strip()
        if not name:
            messages.error(request, "Group name is required.")
            return redirect("dashboard:customer-groups")
        CustomerGroup.objects.create(name=name, color=color, description=description)
        messages.success(request, f"Group '{name}' created.")
        return redirect("dashboard:customer-groups")


class CustomerGroupUpdateView(StaffRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(CustomerGroup, pk=pk)
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6366f1").strip()
        description = request.POST.get("description", "").strip()
        if not name:
            messages.error(request, "Group name is required.")
            return redirect("dashboard:customer-groups")
        group.name = name
        group.color = color
        group.description = description
        group.save()
        messages.success(request, f"Group '{group.name}' updated.")
        return redirect("dashboard:customer-groups")


class CustomerGroupDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(CustomerGroup, pk=pk)
        if group.members.exists():
            messages.error(request, f"Cannot delete '{group.name}' — it has assigned customers. Reassign them first.")
            return redirect("dashboard:customer-groups")
        name = group.name
        group.delete()
        messages.success(request, f"Group '{name}' deleted.")
        return redirect("dashboard:customer-groups")


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
            latitude_value = _parse_decimal_field(latitude, label="Latitude") if latitude else None
            longitude_value = _parse_decimal_field(longitude, label="Longitude") if longitude else None
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
    template_name = "dashboard/site_update.html"

    def get(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        return render(request, self.template_name, {"site": site, "scene_options": SCENE_OPTIONS})

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
            latitude_value = _parse_decimal_field(
                request.POST.get("latitude", "").strip(),
                label="Latitude",
            ) if request.POST.get("latitude", "").strip() else None
            longitude_value = _parse_decimal_field(
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
        site.is_active = is_active
        site.save()

        if site.latitude is None or site.longitude is None:
            HikPartnerService().geocode_site_location(site)
        
        messages.success(request, f"Updated configuration for {site.name}")
        return redirect("dashboard:site-console", pk=pk)


# ---------------------------------------------------------------------------
# Subscription management views
# ---------------------------------------------------------------------------

class SubscriptionListView(StaffRequiredMixin, ListView):
    model = Subscription
    template_name = "dashboard/subscriptions.html"
    context_object_name = "subscriptions"
    ordering = ["status", "next_due_date"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("site", "package")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unsubscribed_sites"] = Site.objects.filter(
            subscription__isnull=True
        ).order_by("name")
        context["current_status"] = self.request.GET.get("status", "")
        today = timezone.localdate()
        context["today"] = today
        context["count_active"] = Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).count()
        context["count_overdue"] = Subscription.objects.filter(status=Subscription.STATUS_OVERDUE).count()
        context["count_suspended"] = Subscription.objects.filter(status=Subscription.STATUS_SUSPENDED).count()
        context["total_mrr"] = (
            Subscription.objects.filter(status=Subscription.STATUS_ACTIVE)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        recent_payments = list(
            SubscriptionPayment.objects.select_related("subscription__site", "recorded_by")
            .order_by("-paid_at")[:20]
        )
        context["recent_payments"] = recent_payments
        context["total_collected_recent"] = sum(p.amount for p in recent_payments)
        for sub in context["subscriptions"]:
            days_delta = (today - sub.next_due_date).days
            setattr(sub, "days_delta", days_delta)
            pct = 0
            if sub.status == Subscription.STATUS_OVERDUE and sub.grace_period_days > 0:
                pct = min(100, int((days_delta / sub.grace_period_days) * 100))
            setattr(sub, "grace_pct", pct)
            setattr(sub, "grace_bar_color", "bg-red-500" if pct >= 80 else "bg-amber-400")
            setattr(sub, "days_until_due", abs(days_delta))
        pkgs = SubscriptionPackage.objects.filter(is_active=True).order_by("monthly_rate")
        context["packages"] = pkgs
        context["packages_json"] = json.dumps([
            {"id": str(p.id), "rate": str(p.monthly_rate), "grace": p.grace_period_days}
            for p in pkgs
        ])
        return context


class CreateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request):
        site_id = request.POST.get("site_id")
        package_id = request.POST.get("package_id", "").strip()
        monthly_rate = request.POST.get("monthly_rate")
        billing_day = request.POST.get("billing_day", "1")
        grace_period_days = request.POST.get("grace_period_days", "7")
        next_due_date = request.POST.get("next_due_date")
        notes = request.POST.get("notes", "")

        if not site_id or not monthly_rate or not next_due_date:
            messages.error(request, "Site, monthly rate, and next due date are required.")
            return redirect("dashboard:subscriptions")

        site = get_object_or_404(Site, pk=site_id)

        if Subscription.objects.filter(site=site).exists():
            messages.error(request, f"'{site.name}' already has a subscription.")
            return redirect("dashboard:subscriptions")

        package = None
        if package_id:
            package = SubscriptionPackage.objects.filter(pk=package_id).first()

        try:
            parsed_rate = _parse_decimal_field(
                monthly_rate,
                label="Monthly rate",
                min_value=Decimal("0.00"),
            )
            parsed_billing_day = _parse_int_field(
                billing_day,
                label="Billing day",
                min_value=1,
                max_value=28,
            )
            parsed_grace_days = _parse_int_field(
                grace_period_days,
                label="Grace period",
                min_value=0,
                max_value=30,
            )
            parsed_due_date = _parse_date_field(next_due_date, label="Next due date")
            status = Subscription.classify_status(
                next_due_date=parsed_due_date,
                grace_period_days=parsed_grace_days,
            )
            Subscription.objects.create(
                site=site,
                monthly_rate=parsed_rate,
                billing_day=parsed_billing_day,
                grace_period_days=parsed_grace_days,
                next_due_date=parsed_due_date,
                notes=notes,
                status=status,
                package=package,
                suspended_at=timezone.now() if status == Subscription.STATUS_SUSPENDED else None,
            )
            messages.success(request, f"Subscription created for '{site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Failed to create subscription: {exc}")

        return redirect("dashboard:subscriptions")


class UpdateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        try:
            sub.monthly_rate = _parse_decimal_field(
                request.POST.get("monthly_rate", ""),
                label="Monthly rate",
                min_value=Decimal("0.00"),
            )
            sub.billing_day = _parse_int_field(
                request.POST.get("billing_day", ""),
                label="Billing day",
                min_value=1,
                max_value=28,
            )
            sub.grace_period_days = _parse_int_field(
                request.POST.get("grace_period_days", ""),
                label="Grace period",
                min_value=0,
                max_value=30,
            )
            sub.next_due_date = _parse_date_field(
                request.POST.get("next_due_date", ""),
                label="Next due date",
            )
            sub.notes = request.POST.get("notes", "").strip()
            package_id = request.POST.get("package_id", "").strip()
            sub.package = SubscriptionPackage.objects.filter(pk=package_id).first() if package_id else None
            sub.apply_due_date_status()
            sub.save()
            messages.success(request, f"Subscription for '{sub.site.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:subscriptions")


class UpdateSubscriptionPaymentView(StaffRequiredMixin, View):
    def post(self, request, payment_id):
        payment = get_object_or_404(SubscriptionPayment, pk=payment_id)
        try:
            original_period_end = payment.period_end
            subscription = payment.subscription
            current_due_anchored_to_payment = (
                subscription.next_due_date == original_period_end + timedelta(days=1)
            )

            payment.amount = _parse_decimal_field(
                request.POST.get("amount", ""),
                label="Amount",
                min_value=Decimal("0.01"),
            )
            parsed_period_start = _parse_date_field(
                request.POST.get("period_start", ""),
                label="Period start",
            )
            parsed_period_end = _parse_date_field(
                request.POST.get("period_end", ""),
                label="Period end",
            )
            if parsed_period_end < parsed_period_start:
                raise ValueError("Period end must be on or after period start.")
            _validate_subscription_payment_window(
                subscription,
                period_start=parsed_period_start,
                period_end=parsed_period_end,
                exclude_payment_id=payment.pk,
            )
            payment.period_start = parsed_period_start
            payment.period_end = parsed_period_end
            payment.method = _parse_payment_method(request.POST.get("method", ""))
            payment.reference = request.POST.get("reference", "").strip()
            payment.notes = request.POST.get("notes", "").strip()
            payment.save()

            latest_payment = subscription.payments.order_by("-period_end", "-paid_at").first()
            if (
                subscription.status != Subscription.STATUS_CANCELLED
                and latest_payment is not None
                and (latest_payment.pk == payment.pk or current_due_anchored_to_payment)
            ):
                subscription.sync_next_due_date_from_latest_payment()
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            messages.success(request, "Payment record updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:subscriptions")


class DeleteSubscriptionPaymentView(StaffRequiredMixin, View):
    def post(self, request, payment_id):
        payment = get_object_or_404(SubscriptionPayment, pk=payment_id)
        site_name = payment.subscription.site.name
        subscription = payment.subscription
        current_due_anchored_to_payment = (
            subscription.next_due_date == payment.period_end + timedelta(days=1)
        )
        deleted_period_start = payment.period_start
        payment.delete()

        if subscription.status != Subscription.STATUS_CANCELLED and current_due_anchored_to_payment:
            if subscription.sync_next_due_date_from_latest_payment():
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            else:
                subscription.next_due_date = deleted_period_start
                subscription.apply_due_date_status()
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
        messages.success(request, f"Payment record for '{site_name}' deleted.")
        return redirect("dashboard:subscriptions")


class RecordPaymentView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        amount = request.POST.get("amount")
        period_start = request.POST.get("period_start")
        period_end = request.POST.get("period_end")
        method = request.POST.get("method", "").strip()
        reference = request.POST.get("reference", "").strip()
        notes = request.POST.get("notes", "")

        if not amount or not period_start or not period_end:
            messages.error(request, "Amount, period start, and period end are required.")
            return redirect("dashboard:subscriptions")

        try:
            parsed_amount = _parse_decimal_field(
                amount,
                label="Amount",
                min_value=Decimal("0.01"),
            )
            parsed_start = _parse_date_field(period_start, label="Period start")
            parsed_end = _parse_date_field(period_end, label="Period end")
            if parsed_end < parsed_start:
                raise ValueError("Period end must be on or after period start.")
            _validate_subscription_payment_window(
                sub,
                period_start=parsed_start,
                period_end=parsed_end,
            )
            SubscriptionPayment.objects.create(
                subscription=sub,
                amount=parsed_amount,
                period_start=parsed_start,
                period_end=parsed_end,
                method=_parse_payment_method(method),
                reference=reference,
                notes=notes,
                recorded_by=request.user,
            )
            new_due = parsed_end + timedelta(days=1)
            sub.next_due_date = new_due
            sub.apply_due_date_status()
            sub.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            messages.success(request, f"Payment recorded for '{sub.site.name}'. Next due: {new_due}.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Failed to record payment: {exc}")

        return redirect("dashboard:subscriptions")


class SuspendSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        if sub.status == Subscription.STATUS_SUSPENDED:
            messages.info(request, f"'{sub.site.name}' subscription is already suspended.")
            return redirect("dashboard:site-console", pk=sub.site.pk)
        else:
            sub.suspend()
            send_suspension_notice.delay(str(sub.id))
            # Log the lockdown as a system event
            Event.objects.create(
                site=sub.site,
                event_type="SITE_LOCKED",
                occurred_at=timezone.now(),
                payload={
                    "event_name": humanize_event_label("SITE_LOCKED"),
                    "normalized_event_type": "site_locked",
                    "reason": "Operator Lockdown",
                    "admin": request.user.username,
                    "message": "Access restricted by dealer operator."
                }
            )
            messages.warning(request, f"Subscription for '{sub.site.name}' has been suspended. Client access is now blocked.")
            return redirect("dashboard:site-console", pk=sub.site.pk)


class CancelSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        if sub.status == Subscription.STATUS_CANCELLED:
            messages.info(request, f"'{sub.site.name}' subscription is already cancelled.")
            return redirect("dashboard:subscriptions")

        sub.status = Subscription.STATUS_CANCELLED
        sub.suspended_at = timezone.now()
        sub.save(update_fields=["status", "suspended_at", "updated_at"])
        send_subscription_lockout_notice.delay(str(sub.id), notice_type="cancelled")
        Event.objects.create(
            site=sub.site,
            event_type="SITE_CANCELLED",
            occurred_at=timezone.now(),
            payload={
                "event_name": humanize_event_label("SITE_CANCELLED"),
                "normalized_event_type": "site_cancelled",
                "reason": "Subscription Cancelled",
                "admin": request.user.username,
                "message": "Billing plan cancelled by operator.",
            },
        )
        messages.warning(request, f"Subscription for '{sub.site.name}' cancelled.")
        return redirect("dashboard:subscriptions")


class ReactivateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        next_due = request.POST.get("next_due_date")
        try:
            new_due = _parse_date_field(next_due, label="Next due date") if next_due else None
            if new_due is not None:
                _validate_reactivation_due_date(sub, new_due)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:site-console", pk=sub.site.pk)

        sub.reactivate(new_due_date=new_due)
        if sub.status != Subscription.STATUS_ACTIVE:
            messages.error(request, "Reactivation did not restore access. Please choose a current or future due date.")
            return redirect("dashboard:site-console", pk=sub.site.pk)
        send_reactivation_notice.delay(str(sub.id))
        # Log the reactivation as a system event
        Event.objects.create(
            site=sub.site,
            event_type="SITE_RESTORED",
            occurred_at=timezone.now(),
            payload={
                "event_name": humanize_event_label("SITE_RESTORED"),
                "normalized_event_type": "site_restored",
                "reason": "Operator Reactivation",
                "admin": request.user.username,
                "message": "Access restored by dealer operator."
            }
        )
        messages.success(request, f"Subscription for '{sub.site.name}' reactivated. Next due: {sub.next_due_date}.")
        return redirect("dashboard:site-console", pk=sub.site.pk)


# ---------------------------------------------------------------------------
# Subscription Packages
# ---------------------------------------------------------------------------

class SubscriptionPackageListView(StaffRequiredMixin, View):
    template_name = "dashboard/packages.html"

    def get(self, request):
        packages = SubscriptionPackage.objects.all()
        return render(request, self.template_name, {"packages": packages})

    def post(self, request):
        name = request.POST.get("name", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        grace_period_days = request.POST.get("grace_period_days", "7").strip()
        description = request.POST.get("description", "").strip()

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            parsed_rate = _parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            parsed_grace = _parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            SubscriptionPackage.objects.create(
                name=name,
                monthly_rate=parsed_rate,
                grace_period_days=parsed_grace,
                description=description,
            )
            messages.success(request, f"Package '{name}' created.")
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect("dashboard:packages")


class UpdateSubscriptionPackageView(StaffRequiredMixin, View):
    def post(self, request, pk):
        pkg = get_object_or_404(SubscriptionPackage, pk=pk)
        name = request.POST.get("name", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        grace_period_days = request.POST.get("grace_period_days", "").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            pkg.name = name
            pkg.monthly_rate = _parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            pkg.grace_period_days = _parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            pkg.description = description
            pkg.is_active = is_active
            pkg.save()
            messages.success(request, f"Package '{pkg.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect("dashboard:packages")


class DeleteSubscriptionPackageView(StaffRequiredMixin, View):
    def post(self, request, pk):
        pkg = get_object_or_404(SubscriptionPackage, pk=pk)
        if pkg.subscriptions.exists():
            messages.error(request, f"Cannot delete '{pkg.name}' — it has linked subscriptions.")
            return redirect("dashboard:packages")
        name = pkg.name
        pkg.delete()
        messages.success(request, f"Package '{name}' deleted.")
        return redirect("dashboard:packages")


# ---------------------------------------------------------------------------
# Client onboarding
# ---------------------------------------------------------------------------

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
    template_name = "dashboard/onboard.html"

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
            validation_user = _password_validation_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            if not password:
                generated_password = _generate_compliant_password(user=validation_user)
                password = generated_password
            else:
                try:
                    _validate_console_password(password, user=validation_user)
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

                profile = user.customer_profile
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
                        parsed_rate = _parse_decimal_field(
                            monthly_rate,
                            label="Monthly rate",
                            min_value=Decimal("0.00"),
                        )
                        parsed_due_date = _parse_date_field(next_due_date, label="First due date")
                        parsed_billing_day = (
                            _parse_int_field(
                                billing_day,
                                label="Billing day",
                                min_value=1,
                                max_value=28,
                            )
                            if billing_day
                            else _billing_day_from_due_date(parsed_due_date)
                        )
                        parsed_grace_days = _parse_int_field(
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
                _send_welcome_email(user, site, generated_password if creating_new_user else None)

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


def _send_welcome_email(user, site, temp_password=None):
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

class PlatformSettingsView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/settings.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings as django_settings

        context = super().get_context_data(**kwargs)
        hik_cfg = django_settings.HIK_PARTNER
        context["settings_groups"] = [
            {
                "title": "Runtime",
                "items": [
                    ("Debug", "Enabled" if django_settings.DEBUG else "Disabled"),
                    ("API Docs", "Enabled" if django_settings.ENABLE_API_DOCS else "Disabled"),
                    ("Database", django_settings.DATABASES["default"]["ENGINE"].rsplit(".", 1)[-1]),
                    ("Email Backend", django_settings.EMAIL_BACKEND.rsplit(".", 1)[-1]),
                ],
            },
            {
                "title": "Hik Platform",
                "items": [
                    ("Configured", "Ready" if hik_cfg["BASE_URL"] and hik_cfg["API_KEY"] and hik_cfg["API_SECRET"] else "Missing credentials"),
                    ("Delivery Mode", hik_cfg.get("DELIVERY_MODE", "mq")),
                    ("Webhook Secret", "Configured" if hik_cfg.get("WEBHOOK_SIGN_SECRET") else "Fallback to API secret"),
                    ("Dry Run", "Enabled" if hik_cfg.get("DRY_RUN") else "Disabled"),
                ],
            },
            {
                "title": "Messaging",
                "items": [
                    ("FCM", "Configured" if django_settings.FIREBASE_CREDENTIALS_PATH else "Not configured"),
                    ("Celery Eager", "Enabled" if django_settings.CELERY_TASK_ALWAYS_EAGER else "Disabled"),
                    ("Broker", django_settings.CELERY_BROKER_URL),
                    ("Result Backend", django_settings.CELERY_RESULT_BACKEND),
                ],
            },
        ]
        context["ops_counts"] = {
            "sites": Site.objects.count(),
            "subscriptions": Subscription.objects.count(),
            "devices": AlarmPanelDevice.objects.count(),
            "mobile_users": User.objects.filter(customer_profile__is_mobile_user=True).count(),
        }
        return context


class BroadcastManagementView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/broadcast.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings as django_settings
        context = super().get_context_data(**kwargs)
        context["device_count"] = FCMDevice.objects.filter(is_active=True).count()
        context["recent_count"] = BroadcastMessage.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        context["users"] = User.objects.filter(customer_profile__is_mobile_user=True).order_by("username")
        context["groups"] = CustomerGroup.objects.annotate(
            member_count=Count("members", distinct=True)
        )
        context["history"] = (
            BroadcastMessage.objects.all()
            .select_related("recipient", "recipient_group")
            .prefetch_related("views")
            .order_by("-created_at")[:20]
        )
        context["fcm_configured"] = bool(django_settings.FIREBASE_CREDENTIALS_PATH)
        context["celery_eager"] = django_settings.CELERY_TASK_ALWAYS_EAGER
        return context

    def post(self, request, *args, **kwargs):
        title = request.POST.get("title")
        body = request.POST.get("body")
        recipient_id = request.POST.get("recipient_id", "").strip()
        group_id = request.POST.get("group_id", "").strip()
        message_type = request.POST.get("type", BroadcastMessage.TYPE_GENERAL)
        if message_type not in {BroadcastMessage.TYPE_GENERAL, BroadcastMessage.TYPE_BILLING, BroadcastMessage.TYPE_ALERT}:
            message_type = BroadcastMessage.TYPE_GENERAL

        send_push = request.POST.get("send_push") == "1"
        send_email = request.POST.get("send_email") == "1"
        send_sms = request.POST.get("send_sms") == "1"

        if not title or not body:
            messages.error(request, "Broadcast title and body are required.")
            return redirect("dashboard:broadcast")
        if not any([send_push, send_email, send_sms]):
            messages.error(request, "Select at least one delivery channel.")
            return redirect("dashboard:broadcast")

        recipient = None
        recipient_group = None
        if recipient_id:
            recipient = get_object_or_404(User, id=recipient_id)
        elif group_id:
            recipient_group = CustomerGroup.objects.filter(pk=group_id).first()

        broadcast = BroadcastMessage.objects.create(
            title=title,
            body=body,
            message_type=message_type,
            send_push=send_push,
            send_email=send_email,
            send_sms=send_sms,
            recipient=recipient,
            recipient_group=recipient_group,
            sent_by=request.user if request.user.is_authenticated else None,
            status=BroadcastMessage.STATUS_PENDING,
        )

        send_broadcast_push_notifications.delay(str(broadcast.id))
        messages.success(request, f"Broadcast '{title}' queued for delivery.")
        return redirect("dashboard:broadcast")


class BroadcastUpdateView(StaffRequiredMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(BroadcastMessage, pk=message_id)
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        message_type = request.POST.get("type", BroadcastMessage.TYPE_GENERAL)
        recipient_id = request.POST.get("recipient_id", "").strip()

        if not title or not body:
            messages.error(request, "Broadcast title and body are required.")
            return redirect("dashboard:broadcast")
        if message_type not in {BroadcastMessage.TYPE_GENERAL, BroadcastMessage.TYPE_BILLING, BroadcastMessage.TYPE_ALERT}:
            message_type = BroadcastMessage.TYPE_GENERAL

        group_id = request.POST.get("group_id", "").strip()
        recipient = None
        recipient_group = None
        if recipient_id:
            recipient = get_object_or_404(User, pk=recipient_id)
        elif group_id:
            recipient_group = CustomerGroup.objects.filter(pk=group_id).first()

        message.title = title
        message.body = body
        message.message_type = message_type
        message.recipient = recipient
        message.recipient_group = recipient_group
        message.send_push = request.POST.get("send_push") == "1"
        message.send_email = request.POST.get("send_email") == "1"
        message.send_sms = request.POST.get("send_sms") == "1"
        message.save(update_fields=[
            "title", "body", "message_type",
            "recipient", "recipient_group",
            "send_push", "send_email", "send_sms",
        ])
        messages.success(request, f"Broadcast '{message.title}' updated.")
        return redirect("dashboard:broadcast")


class BroadcastResendView(StaffRequiredMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(BroadcastMessage, pk=message_id)
        clone = BroadcastMessage.objects.create(
            title=message.title,
            body=message.body,
            message_type=message.message_type,
            recipient=message.recipient,
            sent_by=request.user,
            status=BroadcastMessage.STATUS_PENDING,
        )
        send_broadcast_push_notifications.delay(str(clone.id))
        messages.success(request, f"Broadcast '{message.title}' re-queued for delivery.")
        return redirect("dashboard:broadcast")


class BroadcastDeleteView(StaffRequiredMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(BroadcastMessage, pk=message_id)
        title = message.title
        message.delete()
        messages.success(request, f"Broadcast '{title}' deleted.")
        return redirect("dashboard:broadcast")
