"""Staff console views for operations, users, and platform settings."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, TemplateView, View

from apps.accounts.models import CustomerGroup, FCMDevice, StaffOperatorProfile
from apps.accounts.permissions import ensure_operator_profile, user_has_console_permission
from apps.accounts.rbac import OperatorRole, Perm
from apps.alarms.models import AlarmEvent as Event
from apps.alarms.tasks import refresh_hik_site_health
from apps.communication.models import BroadcastMessage
from apps.communication.tasks import send_broadcast_push_notifications
from apps.dashboard.console_auth import (
    generate_compliant_password,
    password_validation_user,
    validate_console_password,
)
from apps.dashboard.event_presenters import serialize_console_event
from apps.dashboard.permissions import StaffRequiredMixin, SuperuserRequiredMixin
from apps.dashboard.site_helpers import (
    assign_site_operations_zone,
    build_active_faults,
    normalize_zone_color,
    operations_zone_name_taken,
    operations_zones_for_site,
)
from apps.emergency.models import EmergencyRequest
from apps.guarding.models import (
    DispatchTask,
    GuardLocationPing,
    GuardPanicAlert,
    ShiftAssignment,
)
from apps.hik_adapter.services import HikPartnerService
from apps.sites.models import (
    AlarmPanelDevice,
    CustomerSiteAccess,
    OperationsZone,
    Site,
    Subsystem,
    Subscription,
    Zone,
)
from apps.sites.scenes import SCENE_OPTIONS, normalize_scene_label

class DashboardHomeView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/ops/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites_qs = Site.objects.select_related("subscription").prefetch_related("access_list")
        total_sites = sites_qs.count()
        total_panels = AlarmPanelDevice.objects.count()
        online_devices = AlarmPanelDevice.objects.filter(is_online=True).count()
        recent_events = Event.objects.select_related("site", "subsystem", "zone").order_by("-occurred_at")[:12]
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

        from apps.guarding.models import DispatchTask, GuardPanicAlert, ShiftAssignment

        active_dispatch_statuses = [
            DispatchTask.Status.OPEN,
            DispatchTask.Status.ASSIGNED,
            DispatchTask.Status.ACCEPTED,
            DispatchTask.Status.EN_ROUTE,
            DispatchTask.Status.ARRIVED,
        ]
        context["active_emergencies"] = EmergencyRequest.objects.filter(
            status__in=EmergencyRequest.ACTIVE_STATUSES
        ).count()
        context["guard_sos_count"] = GuardPanicAlert.objects.filter(
            status=GuardPanicAlert.Status.OPEN
        ).count()
        context["guard_dispatch_count"] = DispatchTask.objects.filter(
            status__in=active_dispatch_statuses
        ).count()
        context["guards_on_duty"] = ShiftAssignment.objects.filter(
            status=ShiftAssignment.Status.CLOCKED_IN,
            shift__starts_at__lte=now,
            shift__ends_at__gte=now,
        ).count()

        return context

class SiteDirectoryView(StaffRequiredMixin, ListView):
    model = Site
    template_name = "dashboard/sites/directory.html"
    context_object_name = "sites"

    def get_queryset(self):
        qs = super().get_queryset().select_related("subscription", "operations_zone").prefetch_related("devices", "access_list")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(hik_site_id__icontains=query))
        zone_filter = self.request.GET.get("zone", "").strip()
        if zone_filter == "none":
            qs = qs.filter(operations_zone__isnull=True)
        elif zone_filter:
            qs = qs.filter(operations_zone_id=zone_filter)
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
        context["current_zone_filter"] = self.request.GET.get("zone", "")
        context["operations_zones"] = OperationsZone.objects.filter(is_active=True).order_by("sort_order", "name")
        return context

class SiteMapView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/ops/site_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites = Site.objects.select_related("operations_zone").prefetch_related("devices")
        active_emergencies = (
            EmergencyRequest.objects.filter(status__in=EmergencyRequest.ACTIVE_STATUSES)
            .select_related("customer", "site")
            .order_by("-created_at")
        )
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
                    "zone_id": str(site.operations_zone_id) if site.operations_zone_id else None,
                    "zone_name": site.operations_zone.name if site.operations_zone else None,
                    "zone_color": site.operations_zone.color if site.operations_zone else None,
                    "devices": devices,
                    "url": f"/console/sites/{site.id}/"
                })
        
        context["sites_data"] = sites_data
        context["zones_data"] = [
            {
                "id": str(zone.id),
                "name": zone.name,
                "color": zone.color,
                "sort_order": zone.sort_order,
            }
            for zone in OperationsZone.objects.filter(is_active=True).order_by("sort_order", "name")
        ]
        context["emergencies_data"] = [
            {
                "id": str(item.id),
                "customer": item.customer.get_full_name() or item.customer.get_username(),
                "site": item.site.name if item.site else "Away from site",
                "status": item.status,
                "lat": float(item.latitude),
                "lng": float(item.longitude),
                "created_at": item.created_at.isoformat(),
                "url": reverse("dashboard:emergency"),
            }
            for item in active_emergencies
        ]

        from apps.dashboard.api_views import build_guard_map_payload

        guard_payload = build_guard_map_payload()
        context["guards_data"] = guard_payload["guards"]
        context["guard_snapshot"] = guard_payload["snapshot"]
        context["can_manage_zones"] = user_has_console_permission(
            self.request.user, Perm.MANAGE_SITES
        )
        return context


class EmergencyConsoleView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/emergency/dispatch.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requests = (
            EmergencyRequest.objects.select_related("customer", "site", "assigned_to")
            .prefetch_related("location_updates")
            .order_by("-created_at")[:100]
        )
        active_statuses = EmergencyRequest.ACTIVE_STATUSES
        context["emergency_requests"] = requests
        context["assignable_staff"] = User.objects.filter(is_active=True, is_staff=True).order_by("username")
        context["active_count"] = sum(1 for item in requests if item.status in active_statuses)
        context["open_count"] = sum(1 for item in requests if item.status == EmergencyRequest.STATUS_OPEN)
        return context


class EmergencyConsoleAssignView(StaffRequiredMixin, View):
    def post(self, request, request_id):
        emergency = get_object_or_404(EmergencyRequest, pk=request_id)
        if not emergency.is_active:
            messages.error(request, "Closed emergency requests cannot be assigned.")
            return redirect("dashboard:emergency")
        assignee_id = request.POST.get("assigned_to", "").strip()
        assignee = User.objects.filter(pk=assignee_id, is_active=True, is_staff=True).first()
        if assignee is None:
            messages.error(request, "Choose an active staff user to assign.")
            return redirect("dashboard:emergency")
        emergency.assign(
            assignee,
            actor=request.user,
            note=request.POST.get("assignment_note", "").strip(),
        )
        messages.success(request, f"Emergency request assigned to {assignee.username}.")
        return redirect("dashboard:emergency")


class EmergencyConsoleActionView(StaffRequiredMixin, View):
    allowed_actions = {
        "acknowledge": EmergencyRequest.STATUS_ACKNOWLEDGED,
        "dispatch": EmergencyRequest.STATUS_DISPATCHED,
        "arrive": EmergencyRequest.STATUS_ARRIVED,
        "resolve": EmergencyRequest.STATUS_RESOLVED,
        "cancel": EmergencyRequest.STATUS_CANCELLED,
    }

    def post(self, request, request_id, action):
        if action not in self.allowed_actions:
            messages.error(request, "Unsupported emergency action.")
            return redirect("dashboard:emergency")
        emergency = get_object_or_404(EmergencyRequest, pk=request_id)
        emergency.transition(
            self.allowed_actions[action],
            actor=request.user,
            reason=request.POST.get("reason", "").strip(),
        )
        messages.success(request, f"Emergency request marked {self.allowed_actions[action]}.")
        return redirect("dashboard:emergency")


class WebhookLogsView(StaffRequiredMixin, ListView):
    model = Event
    template_name = "dashboard/ops/logs.html"
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

class UserListView(SuperuserRequiredMixin, ListView):
    model = User
    template_name = "dashboard/ops/users.html"
    context_object_name = "users"
    ordering = ["-is_superuser", "username"]

    def get_queryset(self):
        return (
            User.objects.filter(is_staff=True)
            .select_related("operator_profile")
            .order_by("-is_superuser", "username")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["operator_roles"] = OperatorRole.CHOICES
        return context


class CustomerDirectoryView(StaffRequiredMixin, ListView):
    model = User
    template_name = "dashboard/customers/list.html"
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


class StaffUserCreateView(SuperuserRequiredMixin, View):
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
            validate_console_password(
                password,
                user=password_validation_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:user-list")

        role = request.POST.get("role", "").strip() or OperatorRole.OPERATIONS
        valid_roles = {choice[0] for choice in OperatorRole.CHOICES}
        if role not in valid_roles:
            messages.error(request, "Invalid operator role selected.")
            return redirect("dashboard:user-list")
        if is_superuser:
            role = OperatorRole.PLATFORM_ADMIN

        staff_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=is_superuser,
        )
        StaffOperatorProfile.objects.create(user=staff_user, role=role)
        messages.success(request, f"Staff user '{username}' created.")
        return redirect("dashboard:user-list")


class StaffUserUpdateView(SuperuserRequiredMixin, View):
    def post(self, request, user_id):
        staff_user = get_object_or_404(User, pk=user_id, is_staff=True)
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        is_superuser = request.POST.get("is_superuser") == "on"
        is_active = request.POST.get("is_active") == "on"
        role = request.POST.get("role", "").strip() or OperatorRole.OPERATIONS
        valid_roles = {choice[0] for choice in OperatorRole.CHOICES}
        if role not in valid_roles:
            messages.error(request, "Invalid operator role selected.")
            return redirect("dashboard:user-list")
        if is_superuser:
            role = OperatorRole.PLATFORM_ADMIN

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
                validate_console_password(
                    password,
                    user=password_validation_user(
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
        profile, _ = StaffOperatorProfile.objects.get_or_create(
            user=staff_user,
            defaults={"role": role},
        )
        if profile.role != role:
            profile.role = role
            profile.save(update_fields=["role", "updated_at"])
        messages.success(request, f"Staff user '{staff_user.username}' updated.")
        return redirect("dashboard:user-list")


class StaffUserDeleteView(SuperuserRequiredMixin, View):
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
            validate_console_password(
                password,
                user=password_validation_user(
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
                validate_console_password(
                    password,
                    user=password_validation_user(
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
    template_name = "dashboard/customers/groups.html"

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


class MapZoneListView(StaffRequiredMixin, View):
    template_name = "dashboard/ops/map_zones.html"

    def get(self, request):
        zone_sites = Site.objects.only(
            "id",
            "name",
            "address",
            "city",
            "country",
            "hik_site_id",
            "is_active",
            "operations_zone",
        ).order_by("name")
        zones = (
            OperationsZone.objects.annotate(site_count=Count("sites"))
            .prefetch_related(Prefetch("sites", queryset=zone_sites))
            .order_by("sort_order", "name")
        )
        zone_summary = {
            "active": OperationsZone.objects.filter(is_active=True).count(),
            "hidden": OperationsZone.objects.filter(is_active=False).count(),
            "assigned_sites": Site.objects.filter(operations_zone__isnull=False).count(),
            "unassigned_sites": Site.objects.filter(operations_zone__isnull=True).count(),
        }
        return render(request, self.template_name, {"zones": zones, "zone_summary": zone_summary})

    def post(self, request):
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6366f1").strip()
        description = request.POST.get("description", "").strip()
        sort_order_raw = request.POST.get("sort_order", "0").strip()
        try:
            sort_order = max(0, int(sort_order_raw or 0))
        except ValueError:
            sort_order = 0
        if not name:
            messages.error(request, "Zone name is required.")
            return redirect("dashboard:map-zones")
        if operations_zone_name_taken(name):
            messages.error(request, f"A zone named '{name}' already exists.")
            return redirect("dashboard:map-zones")
        OperationsZone.objects.create(
            name=name,
            color=normalize_zone_color(color),
            description=description,
            sort_order=sort_order,
        )
        messages.success(request, f"Zone '{name}' created.")
        return redirect("dashboard:map-zones")


class MapZoneUpdateView(StaffRequiredMixin, View):
    def post(self, request, pk):
        zone = get_object_or_404(OperationsZone, pk=pk)
        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#6366f1").strip()
        description = request.POST.get("description", "").strip()
        sort_order_raw = request.POST.get("sort_order", "0").strip()
        is_active = request.POST.get("is_active") == "on"
        try:
            sort_order = max(0, int(sort_order_raw or 0))
        except ValueError:
            sort_order = zone.sort_order
        if not name:
            messages.error(request, "Zone name is required.")
            return redirect("dashboard:map-zones")
        if operations_zone_name_taken(name, exclude_pk=zone.pk):
            messages.error(request, f"A zone named '{name}' already exists.")
            return redirect("dashboard:map-zones")
        zone.name = name
        zone.color = normalize_zone_color(color)
        zone.description = description
        zone.sort_order = sort_order
        zone.is_active = is_active
        zone.save()
        messages.success(request, f"Zone '{zone.name}' updated.")
        return redirect("dashboard:map-zones")


class MapZoneDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        zone = get_object_or_404(OperationsZone, pk=pk)
        name = zone.name
        site_count = zone.sites.count()
        zone.delete()
        if site_count:
            messages.success(request, f"Zone '{name}' deleted. {site_count} site(s) moved to Unassigned.")
        else:
            messages.success(request, f"Zone '{name}' deleted.")
        return redirect("dashboard:map-zones")


class PlatformSettingsView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/ops/settings.html"

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
    template_name = "dashboard/ops/broadcast.html"

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
