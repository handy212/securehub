from datetime import date, datetime, timedelta
import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
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
from apps.sites.models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, CustomerSiteAccess, OperationsZone, Site, Subsystem, Subscription, SubscriptionPackage, SubscriptionPayment, Zone
from apps.sites.scenes import SCENE_OPTIONS, normalize_scene_label
from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import Perm


def _normalize_zone_color(color: str, default: str = "#6366f1") -> str:
    value = (color or "").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.lower()
        except ValueError:
            pass
    return default


def _operations_zone_name_taken(name: str, *, exclude_pk=None) -> bool:
    qs = OperationsZone.objects.filter(name__iexact=name.strip())
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _operations_zones_for_site(site=None):
    qs = OperationsZone.objects.all()
    if site is not None:
        qs = qs.filter(Q(is_active=True) | Q(pk=site.operations_zone_id))
    else:
        qs = qs.filter(is_active=True)
    return qs.order_by("sort_order", "name")


def _assign_site_operations_zone(site, zone_id: str) -> None:
    zone_id = (zone_id or "").strip()
    if not zone_id:
        site.operations_zone = None
        return
    site.operations_zone = OperationsZone.objects.filter(pk=zone_id).first()
from apps.accounts.models import CustomerGroup, FCMDevice
from apps.communication.models import BroadcastMessage
from apps.communication.tasks import send_broadcast_push_notifications
from apps.emergency.models import (
    AccountEmergencyService,
    EmergencyRequest,
    EmergencyServicePlan,
    EmergencyServiceStatus,
    SiteEmergencyService,
)
from apps.guarding.models import (
    Checkpoint,
    CheckpointScan,
    ClientPortalAccess,
    ClockEvent,
    DispatchTask,
    FieldReport,
    FieldReportAcknowledgement,
    FieldReportAttachment,
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantEducation,
    GuardApplicantEmployment,
    GuardApplicantProfile,
    GuardApplicantReference,
    GuardAvailability,
    GuardContract,
    GuardCredential,
    GuardDocument,
    GuardEquipmentIssue,
    GuardInvoice,
    GuardInvoiceLine,
    GuardOffboardingChecklist,
    GuardTimesheet,
    GuardTrainingRecord,
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    LeaveRequest,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    PostOrder,
    ReportTemplate,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    ShiftTemplate,
    SiteGuardDispatchPolicy,
    WelfareCheck,
)
from apps.guarding.applicant_forms import populate_applicant_from_request, populate_applicant_profile_from_request
from apps.guarding.services import (
    acknowledge_panic_alert,
    apply_credential_verification,
    complete_patrol_round,
    count_non_compliant_active_guards,
    ensure_applicant_status_transition,
    ensure_guard_compliance_ready,
    ensure_guard_status_transition,
    guard_compliance_issues,
    ensure_panic_alert_status_transition,
    ensure_report_status_transition,
    ensure_shift_status_transition,
    hire_applicant,
    record_clock_event,
    review_leave_request,
    review_shift_swap_request,
    acknowledge_field_report,
    review_field_report,
    review_timesheet,
    resolve_panic_alert,
    transition_assignment,
    transition_dispatch_task,
    transition_panic_alert,
    transition_patrol_round,
    transition_shift,
    generate_guard_invoice,
    transition_guard_invoice,
)
from apps.dashboard.event_presenters import serialize_console_event, should_hide_console_event
from apps.accounts.permissions import ensure_operator_profile, user_can_access_console
from apps.accounts.models import StaffOperatorProfile
from apps.accounts.rbac import OperatorRole
from apps.accounts.serializers import resolve_username_for_login
from apps.dashboard.permissions import StaffRequiredMixin, SuperuserRequiredMixin


class GuardingClientRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return bool(
            self.request.user.is_authenticated
            and ClientPortalAccess.objects.filter(user=self.request.user).exists()
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={self.request.get_full_path()}"
            return redirect(login_url)
        return HttpResponseForbidden("Guarding client access required.")


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
    template_name = "dashboard/auth/login.html"

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
        auth_username = resolve_username_for_login(username)
        user = authenticate(request, username=auth_username, password=password)
        if user is not None and user.is_staff and user_can_access_console(user):
            ensure_operator_profile(user)
            _clear_console_login_failures(request, username)
            login(request, user)
            return redirect(next_url)
        _record_console_login_failure(request, username)
        return render(request, self.template_name, {
            "error": "Invalid credentials or insufficient permissions.",
            "next": next_url,
        })


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


def _guarding_redirect(target, *, anchor=""):
    url = reverse(target)
    return f"{url}#{anchor}" if anchor else url


def _parse_datetime_field(raw_value, *, label):
    value = parse_datetime(str(raw_value or "").strip())
    if value is None:
        raise ValueError(f"{label} must be a valid date and time.")
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _parse_date_field(raw_value, *, label):
    value = parse_date(str(raw_value or "").strip())
    if value is None:
        raise ValueError(f"{label} must be a valid date.")
    return value


def _parse_optional_date_field(raw_value, *, label):
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    return _parse_date_field(raw, label=label)


def _populate_guard_profile_from_post(guard, request) -> None:
    from apps.guarding.guard_forms import populate_guard_profile_from_request

    populate_guard_profile_from_request(
        guard,
        request,
        parse_optional_date=_parse_optional_date_field,
    )


def _attach_guard_compliance_flags(guards) -> None:
    for guard in guards:
        guard.compliance_issues = guard_compliance_issues(guard)
        guard.is_compliance_ready = not guard.compliance_issues


def _apply_credential_from_post(credential, request, *, actor) -> None:
    credential.credential_type = request.POST.get("credential_type") or GuardCredential.CredentialType.OTHER
    credential.name = request.POST.get("name", "").strip()
    credential.issuing_authority = request.POST.get("issuing_authority", "").strip()
    credential.reference_number = request.POST.get("reference_number", "").strip()
    credential.issued_on = request.POST.get("issued_on") or None
    credential.expires_on = request.POST.get("expires_on") or None
    credential.notes = request.POST.get("notes", "").strip()
    apply_credential_verification(credential, verified=bool(request.POST.get("verified")), actor=actor)


def _parse_time_field(raw_value, *, label):
    value = parse_time(str(raw_value or "").strip())
    if value is None:
        raise ValueError(f"{label} must be a valid time.")
    return value


def _csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


class GuardingOverviewMixin:
    def get_guarding_counts(self):
        active_dispatch_statuses = [
            DispatchTask.Status.OPEN,
            DispatchTask.Status.ASSIGNED,
            DispatchTask.Status.ACCEPTED,
            DispatchTask.Status.EN_ROUTE,
            DispatchTask.Status.ARRIVED,
        ]
        counts = {
            "guards": GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).count(),
            "applicants": GuardApplicant.objects.exclude(
                status__in=[
                    GuardApplicant.Status.HIRED,
                    GuardApplicant.Status.REJECTED,
                    GuardApplicant.Status.WITHDRAWN,
                ]
            ).count(),
            "posts": GuardPost.objects.filter(is_active=True).count(),
            "open_dispatch": DispatchTask.objects.filter(status__in=active_dispatch_statuses).count(),
            "open_panic": GuardPanicAlert.objects.filter(status=GuardPanicAlert.Status.OPEN).count(),
            "welfare_due": WelfareCheck.objects.filter(
                status__in=[WelfareCheck.Status.PENDING, WelfareCheck.Status.ESCALATED]
            ).count(),
            "non_compliant_guards": count_non_compliant_active_guards(),
        }
        try:
            from apps.guarding.asset_services import asset_analytics_summary

            asset_stats = asset_analytics_summary()
            counts["open_manifests"] = asset_stats["open_manifests"]
            counts["assets_out"] = asset_stats["units_out"]
            counts["overdue_asset_returns"] = asset_stats["overdue_returns"]
        except Exception:
            counts["open_manifests"] = 0
            counts["assets_out"] = 0
            counts["overdue_asset_returns"] = 0
        return counts


class GuardingOverviewView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()
        day_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time()),
            timezone.get_current_timezone(),
        )
        day_end = day_start + timedelta(days=1)
        active_dispatch_statuses = [
            DispatchTask.Status.OPEN,
            DispatchTask.Status.ASSIGNED,
            DispatchTask.Status.ACCEPTED,
            DispatchTask.Status.EN_ROUTE,
            DispatchTask.Status.ARRIVED,
        ]
        context["counts"] = self.get_guarding_counts()
        todays_shifts = Shift.objects.filter(starts_at__lt=day_end, ends_at__gte=day_start)
        required_guards_today = todays_shifts.aggregate(total=Sum("required_guards"))["total"] or 0
        assigned_guards_today = ShiftAssignment.objects.filter(shift__in=todays_shifts).exclude(
            status__in=[ShiftAssignment.Status.DECLINED, ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW]
        ).count()
        context["today_summary"] = {
            "shifts": todays_shifts.count(),
            "required_guards": required_guards_today,
            "assigned_guards": assigned_guards_today,
            "coverage_gap": max(required_guards_today - assigned_guards_today, 0),
            "coverage_percent": min(100, round((assigned_guards_today / required_guards_today) * 100))
            if required_guards_today
            else 0,
            "clocked_in": ShiftAssignment.objects.filter(
                shift__in=todays_shifts,
                status=ShiftAssignment.Status.CLOCKED_IN,
            ).count(),
            "patrol_scans": CheckpointScan.objects.filter(scanned_at__gte=day_start, scanned_at__lt=day_end).count(),
            "reports": FieldReport.objects.filter(submitted_at__gte=day_start, submitted_at__lt=day_end).count(),
        }
        context["open_panic_alerts"] = (
            GuardPanicAlert.objects.select_related("guard", "site")
            .filter(status=GuardPanicAlert.Status.OPEN)
            .order_by("-created_at")[:8]
        )
        context["active_dispatch_tasks"] = (
            DispatchTask.objects.select_related("site", "assigned_guard")
            .filter(status__in=active_dispatch_statuses)
            .order_by("-created_at")[:8]
        )
        context["upcoming_shifts"] = (
            Shift.objects.select_related("post", "post__site")
            .prefetch_related("assignments__guard")
            .filter(ends_at__gte=now)
            .order_by("starts_at")[:8]
        )
        context["welfare_checks"] = (
            WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post")
            .filter(status__in=[WelfareCheck.Status.PENDING, WelfareCheck.Status.ESCALATED])
            .order_by("due_at")[:8]
        )
        context["recent_scans"] = (
            CheckpointScan.objects.select_related("checkpoint", "guard", "patrol_round", "patrol_round__route")
            .order_by("-scanned_at")[:8]
        )
        context["recent_reports"] = (
            FieldReport.objects.select_related("site", "post", "guard")
            .order_by("-submitted_at")[:8]
        )
        context["workflow_events"] = (
            GuardingEventLog.objects.select_related("guard", "site", "actor")
            .order_by("-created_at")[:10]
        )
        context["workflow_event_counts"] = {
            "critical": GuardingEventLog.objects.filter(severity=GuardingEventLog.Severity.CRITICAL).count(),
            "warning": GuardingEventLog.objects.filter(severity=GuardingEventLog.Severity.WARNING).count(),
        }
        expiry_cutoff = today + timedelta(days=30)
        context["backoffice_summary"] = {
            "active_contracts": GuardContract.objects.filter(status=GuardContract.Status.ACTIVE).count(),
            "draft_timesheets": GuardTimesheet.objects.filter(status=GuardTimesheet.Status.DRAFT).count(),
            "pending_timesheets": GuardTimesheet.objects.filter(status=GuardTimesheet.Status.SUBMITTED).count(),
            "expiring_credentials": GuardCredential.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
            "expiring_documents": GuardDocument.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
            "expiring_training": GuardTrainingRecord.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
        }
        return context


class GuardingApplicantsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/applicants.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applicants = (
            GuardApplicant.objects.select_related("hired_guard", "created_by", "profile")
            .prefetch_related("documents", "education_records", "employment_records", "references")
            .order_by("-created_at")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            applicants = applicants.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(national_id__icontains=query)
            )
        context["applicants"] = applicants[:200]
        context["statuses"] = GuardApplicant.Status.choices
        context["background_check_statuses"] = [
            ("pending", "Pending"),
            ("clear", "Clear"),
            ("failed", "Failed"),
        ]
        context["gender_choices"] = [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not", "Prefer not to say"),
        ]
        context["marital_status_choices"] = [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
            ("other", "Other"),
        ]
        context["shift_preference_choices"] = GuardApplicantProfile.ShiftPreference.choices
        context["applicant_document_types"] = GuardApplicantDocument.DocumentType.choices
        context["public_apply_url"] = self.request.build_absolute_uri("/apply/guard/")
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["new_applicant"] = GuardApplicant(status=GuardApplicant.Status.APPLIED)
        return context

    def _save_applicant_core(self, applicant, request):
        if not applicant.first_name or not applicant.last_name:
            raise ValueError("First name and last name are required.")
        next_status = request.POST.get("status") or applicant.status or GuardApplicant.Status.APPLIED
        ensure_applicant_status_transition(applicant, next_status)
        applicant.status = next_status
        applicant.save()
        populate_applicant_profile_from_request(applicant, request, parse_dates=_parse_date_field)

    def post(self, request):
        action = request.POST.get("action", "applicant")
        parse_date = _parse_date_field
        try:
            if action == "update_applicant":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                populate_applicant_from_request(applicant, request, parse_dates=parse_date)
                self._save_applicant_core(applicant, request)
                messages.success(request, "Applicant updated.")
            elif action == "delete_applicant":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                if applicant.hired_guard_id:
                    raise ValueError("Hired applicants are linked to guard profiles and cannot be deleted here.")
                applicant.delete()
                messages.success(request, "Applicant deleted.")
            elif action == "applicant_document":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                upload = request.FILES.get("file")
                if not upload:
                    raise ValueError("Document file is required.")
                GuardApplicantDocument.objects.create(
                    applicant=applicant,
                    document_type=request.POST.get("document_type") or GuardApplicantDocument.DocumentType.OTHER,
                    title=request.POST.get("title", "").strip() or upload.name,
                    file=upload,
                    reference_number=request.POST.get("reference_number", "").strip(),
                    notes=request.POST.get("notes", "").strip(),
                    uploaded_by=request.user,
                )
                messages.success(request, "Document uploaded.")
            elif action == "delete_applicant_document":
                get_object_or_404(GuardApplicantDocument, pk=request.POST.get("document_id")).delete()
                messages.success(request, "Document deleted.")
            elif action in {"applicant_education", "update_applicant_education"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantEducation, pk=request.POST.get("education_id"))
                    if action == "update_applicant_education"
                    else GuardApplicantEducation(applicant=applicant)
                )
                record.education_level = request.POST.get("education_level", "").strip()
                if not record.education_level:
                    raise ValueError("Education level is required.")
                record.institution_name = request.POST.get("institution_name", "").strip()
                year_raw = request.POST.get("year_completed", "").strip()
                record.year_completed = int(year_raw) if year_raw else None
                record.certificates_obtained = request.POST.get("certificates_obtained", "").strip()
                record.save()
                messages.success(request, "Education record saved.")
            elif action == "delete_applicant_education":
                get_object_or_404(GuardApplicantEducation, pk=request.POST.get("education_id")).delete()
                messages.success(request, "Education record deleted.")
            elif action in {"applicant_employment", "update_applicant_employment"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantEmployment, pk=request.POST.get("employment_id"))
                    if action == "update_applicant_employment"
                    else GuardApplicantEmployment(applicant=applicant)
                )
                record.company_name = request.POST.get("company_name", "").strip()
                if not record.company_name:
                    raise ValueError("Company name is required.")
                record.position = request.POST.get("position", "").strip()
                record.duties = request.POST.get("duties", "").strip()
                record.supervisor_name = request.POST.get("supervisor_name", "").strip()
                record.supervisor_contact = request.POST.get("supervisor_contact", "").strip()
                record.reason_for_leaving = request.POST.get("reason_for_leaving", "").strip()
                years_raw = request.POST.get("years_experience", "").strip()
                record.years_experience = Decimal(years_raw) if years_raw else None
                if request.POST.get("started_on"):
                    record.started_on = parse_date(request.POST.get("started_on"), label="Start date")
                if request.POST.get("ended_on"):
                    record.ended_on = parse_date(request.POST.get("ended_on"), label="End date")
                record.save()
                messages.success(request, "Employment record saved.")
            elif action == "delete_applicant_employment":
                get_object_or_404(GuardApplicantEmployment, pk=request.POST.get("employment_id")).delete()
                messages.success(request, "Employment record deleted.")
            elif action in {"applicant_reference", "update_applicant_reference"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantReference, pk=request.POST.get("reference_id"))
                    if action == "update_applicant_reference"
                    else GuardApplicantReference(applicant=applicant)
                )
                record.full_name = request.POST.get("full_name", "").strip()
                if not record.full_name:
                    raise ValueError("Reference name is required.")
                record.company = request.POST.get("company", "").strip()
                record.position = request.POST.get("position", "").strip()
                record.phone_number = request.POST.get("phone_number", "").strip()
                record.save()
                messages.success(request, "Reference saved.")
            elif action == "delete_applicant_reference":
                get_object_or_404(GuardApplicantReference, pk=request.POST.get("reference_id")).delete()
                messages.success(request, "Reference deleted.")
            elif action == "applicant":
                applicant = GuardApplicant(created_by=request.user, status=GuardApplicant.Status.APPLIED)
                populate_applicant_from_request(applicant, request, parse_dates=parse_date)
                self._save_applicant_core(applicant, request)
                messages.success(request, "Applicant created.")
            else:
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-applicants")


class GuardingApplicantHireView(StaffRequiredMixin, View):
    def post(self, request, applicant_id):
        applicant = get_object_or_404(GuardApplicant, pk=applicant_id)
        try:
            guard = hire_applicant(
                applicant,
                employee_number=request.POST.get("employee_number", "").strip(),
                actor=request.user,
            )
            messages.success(request, f"{guard.full_name} hired as {guard.employee_number}.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-applicants")


class GuardingApplicantPdfView(StaffRequiredMixin, View):
    def get(self, request, applicant_id):
        from apps.guarding.reports.pdf import render_guard_applicant_pdf

        applicant = get_object_or_404(GuardApplicant, pk=applicant_id)
        pdf_bytes = render_guard_applicant_pdf(applicant)
        filename = f"guard-application-{applicant.last_name}-{applicant.pk}.pdf".replace(" ", "-")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class GuardingGuardsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/guards.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guards = (
            GuardProfile.objects.select_related("user", "supervisor")
            .prefetch_related("credentials", "documents")
            .order_by("last_name", "first_name")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            guards = guards.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(employee_number__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(email__icontains=query)
                | Q(metadata__national_id__icontains=query)
            )
        guards = list(guards[:200])
        _attach_guard_compliance_flags(guards)
        context["guards"] = guards
        context["users"] = User.objects.filter(is_active=True).order_by("username")
        context["supervisors"] = User.objects.filter(is_active=True, is_staff=True).order_by("username")
        context["statuses"] = GuardProfile.Status.choices
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["credential_types"] = GuardCredential.CredentialType.choices
        context["document_types"] = GuardDocument.DocumentType.choices
        from apps.guarding.guard_forms import guard_form_choices

        context.update(guard_form_choices())
        context["credentials"] = (
            GuardCredential.objects.select_related("guard", "verified_by")
            .order_by("expires_on", "name")[:100]
        )
        context["documents"] = GuardDocument.objects.select_related("guard", "uploaded_by").order_by("-created_at")[:100]
        context["location_pings"] = GuardLocationPing.objects.select_related("guard", "assignment").order_by("-created_at")[:100]
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        return context

    def post(self, request):
        action = request.POST.get("action", "guard")
        if action == "update_guard":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                employee_number = request.POST.get("employee_number", "").strip()
                first_name = request.POST.get("first_name", "").strip()
                last_name = request.POST.get("last_name", "").strip()
                if not employee_number or not first_name or not last_name:
                    raise ValueError("Employee number, first name, and last name are required.")
                if GuardProfile.objects.filter(employee_number=employee_number).exclude(pk=guard.pk).exists():
                    raise ValueError("Employee number is already in use.")
                guard.user = User.objects.filter(pk=request.POST.get("user_id")).first()
                guard.supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
                guard.employee_number = employee_number
                guard.first_name = first_name
                guard.last_name = last_name
                _populate_guard_profile_from_post(guard, request)
                next_status = request.POST.get("status") or GuardProfile.Status.ACTIVE
                ensure_guard_status_transition(guard, next_status)
                guard.status = next_status
                if guard.status == GuardProfile.Status.TERMINATED and not guard.termination_date:
                    guard.termination_date = timezone.localdate()
                guard.save(
                    update_fields=[
                        "user",
                        "supervisor",
                        "employee_number",
                        "first_name",
                        "last_name",
                        "phone_number",
                        "email",
                        "home_address",
                        "emergency_contact_name",
                        "emergency_contact_phone",
                        "hire_date",
                        "termination_date",
                        "notes",
                        "metadata",
                        "status",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard profile updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_guard":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                guard.delete()
                messages.success(request, "Guard profile deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_credential":
            try:
                credential = get_object_or_404(GuardCredential, pk=request.POST.get("credential_id"))
                credential.delete()
                messages.success(request, "Guard credential deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_credential":
            try:
                credential = get_object_or_404(GuardCredential, pk=request.POST.get("credential_id"))
                credential.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                _apply_credential_from_post(credential, request, actor=request.user)
                credential.save(
                    update_fields=[
                        "guard",
                        "credential_type",
                        "name",
                        "issuing_authority",
                        "reference_number",
                        "issued_on",
                        "expires_on",
                        "verified",
                        "verified_by",
                        "verified_at",
                        "notes",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard credential updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_document":
            try:
                document = get_object_or_404(GuardDocument, pk=request.POST.get("document_id"))
                document.delete()
                messages.success(request, "Guard document deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "location_ping":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                GuardLocationPing.objects.create(
                    guard=guard,
                    assignment=ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first(),
                    latitude=_parse_decimal_field(request.POST.get("latitude"), label="Latitude"),
                    longitude=_parse_decimal_field(request.POST.get("longitude"), label="Longitude"),
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    speed_mps=request.POST.get("speed_mps") or None,
                    heading_deg=request.POST.get("heading_deg") or None,
                    device_timestamp=_parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None,
                )
                messages.success(request, "Location ping recorded.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_location_ping":
            try:
                ping = get_object_or_404(GuardLocationPing, pk=request.POST.get("location_ping_id"))
                ping.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                ping.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                ping.latitude = _parse_decimal_field(request.POST.get("latitude"), label="Latitude")
                ping.longitude = _parse_decimal_field(request.POST.get("longitude"), label="Longitude")
                ping.accuracy_m = request.POST.get("accuracy_m") or None
                ping.speed_mps = request.POST.get("speed_mps") or None
                ping.heading_deg = request.POST.get("heading_deg") or None
                ping.device_timestamp = (
                    _parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None
                )
                ping.save()
                messages.success(request, "Location ping updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_location_ping":
            try:
                ping = get_object_or_404(GuardLocationPing, pk=request.POST.get("location_ping_id"))
                ping.delete()
                messages.success(request, "Location ping deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_document":
            try:
                document = get_object_or_404(GuardDocument, pk=request.POST.get("document_id"))
                upload = request.FILES.get("file")
                document.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                document.document_type = request.POST.get("document_type") or GuardDocument.DocumentType.OTHER
                document.title = request.POST.get("title", "").strip()
                document.reference_number = request.POST.get("reference_number", "").strip()
                document.expires_on = request.POST.get("expires_on") or None
                document.notes = request.POST.get("notes", "").strip()
                if upload:
                    document.file = upload
                document.save()
                messages.success(request, "Guard document updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "credential":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                credential = GuardCredential(guard=guard)
                _apply_credential_from_post(credential, request, actor=request.user)
                credential.save()
                messages.success(request, "Guard credential created.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "document":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                GuardDocument.objects.create(
                    guard=guard,
                    document_type=request.POST.get("document_type") or GuardDocument.DocumentType.OTHER,
                    title=request.POST.get("title", "").strip(),
                    file=request.FILES.get("file"),
                    reference_number=request.POST.get("reference_number", "").strip(),
                    expires_on=request.POST.get("expires_on") or None,
                    notes=request.POST.get("notes", "").strip(),
                    uploaded_by=request.user,
                )
                messages.success(request, "Guard document recorded.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        employee_number = request.POST.get("employee_number", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        if not employee_number or not first_name or not last_name:
            messages.error(request, "Employee number, first name, and last name are required.")
            return redirect("dashboard:guarding-guards")
        if GuardProfile.objects.filter(employee_number=employee_number).exists():
            messages.error(request, "Employee number is already in use.")
            return redirect("dashboard:guarding-guards")
        user = User.objects.filter(pk=request.POST.get("user_id")).first()
        supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
        next_status = request.POST.get("status") or GuardProfile.Status.INACTIVE
        guard = GuardProfile(
            user=user,
            employee_number=employee_number,
            first_name=first_name,
            last_name=last_name,
            supervisor=supervisor,
            status=next_status,
            hire_date=timezone.localdate(),
        )
        _populate_guard_profile_from_post(guard, request)
        if next_status == GuardProfile.Status.ACTIVE:
            try:
                ensure_guard_compliance_ready(guard)
            except Exception as exc:
                messages.error(request, str(exc))
                return redirect("dashboard:guarding-guards")
        guard.save()
        messages.success(request, "Guard profile created.")
        return redirect("dashboard:guarding-guards")


class GuardingPostsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/posts.html"

    def get_context_data(self, **kwargs):
        from .guarding_asset_console import posts_asset_context

        context = super().get_context_data(**kwargs)
        context.update(posts_asset_context())
        context["all_posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        posts = GuardPost.objects.select_related("site", "supervisor").order_by("site__name", "name")
        query = self.request.GET.get("q", "").strip()
        if query:
            posts = posts.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(site__name__icontains=query))
        context["posts"] = posts[:200]
        context["sites"] = Site.objects.order_by("name")
        context["supervisors"] = User.objects.filter(is_active=True, is_staff=True).order_by("username")
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["post_orders"] = PostOrder.objects.select_related("post", "post__site", "created_by").order_by("post__site__name", "post__name", "-created_at")[:200]
        return context

    def post(self, request):
        from .guarding_asset_console import handle_posts_asset_action

        action = request.POST.get("action", "post")
        if handle_posts_asset_action(request):
            return redirect("dashboard:guarding-posts")
        if action == "update_post":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                name = request.POST.get("name", "").strip()
                if not name:
                    raise ValueError("Post name is required.")
                post.site = site
                post.name = name
                post.code = request.POST.get("code", "").strip()
                post.description = request.POST.get("description", "").strip()
                post.geofence_radius_m = _parse_int_field(
                    request.POST.get("geofence_radius_m") or 150,
                    label="Geofence radius",
                    min_value=1,
                )
                post.supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
                post.is_active = not bool(request.POST.get("inactive"))
                post.save(
                    update_fields=[
                        "site",
                        "name",
                        "code",
                        "description",
                        "geofence_radius_m",
                        "supervisor",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard post updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "delete_post":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                post.delete()
                messages.success(request, "Guard post deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "update_post_order":
            try:
                order = get_object_or_404(PostOrder, pk=request.POST.get("order_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                title = request.POST.get("title", "").strip()
                body = request.POST.get("body", "").strip()
                if not title or not body:
                    raise ValueError("Order title and body are required.")
                order.post = post
                order.title = title
                order.body = body
                order.effective_from = request.POST.get("effective_from") or None
                order.effective_until = request.POST.get("effective_until") or None
                order.is_active = not bool(request.POST.get("inactive"))
                order.save(
                    update_fields=[
                        "post",
                        "title",
                        "body",
                        "effective_from",
                        "effective_until",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Post order updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "delete_post_order":
            try:
                order = get_object_or_404(PostOrder, pk=request.POST.get("order_id"))
                order.delete()
                messages.success(request, "Post order deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "post_order":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                PostOrder.objects.create(
                    post=post,
                    title=request.POST.get("title", "").strip(),
                    body=request.POST.get("body", "").strip(),
                    effective_from=request.POST.get("effective_from") or None,
                    effective_until=request.POST.get("effective_until") or None,
                    is_active=not bool(request.POST.get("inactive")),
                    created_by=request.user,
                )
                messages.success(request, "Post order created.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        site = get_object_or_404(Site, pk=request.POST.get("site_id"))
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Post name is required.")
            return redirect("dashboard:guarding-posts")
        supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
        try:
            GuardPost.objects.create(
                site=site,
                name=name,
                code=request.POST.get("code", "").strip(),
                description=request.POST.get("description", "").strip(),
                geofence_radius_m=_parse_int_field(
                    request.POST.get("geofence_radius_m") or 150,
                    label="Geofence radius",
                    min_value=1,
                ),
                supervisor=supervisor,
            )
            messages.success(request, "Guard post created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-posts")


class GuardingShiftsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/shifts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shifts"] = (
            Shift.objects.select_related("post", "post__site")
            .prefetch_related("assignments__guard", "assignments__assigned_by")
            .order_by("-starts_at")[:200]
        )
        context["posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        guards = list(
            GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        )
        _attach_guard_compliance_flags(guards)
        context["guards"] = guards
        context["assignments"] = (
            ShiftAssignment.objects.select_related("shift", "shift__post", "guard", "assigned_by")
            .order_by("-shift__starts_at")[:200]
        )
        context["clock_events"] = ClockEvent.objects.select_related("assignment", "assignment__guard", "assignment__shift__post").order_by("-created_at")[:100]
        context["welfare_checks"] = WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post").order_by("due_at")[:100]
        context["statuses"] = Shift.Status.choices
        context["assignment_statuses"] = ShiftAssignment.Status.choices
        context["clock_event_types"] = ClockEvent.EventType.choices
        context["welfare_statuses"] = WelfareCheck.Status.choices
        context["counts"] = self.get_guarding_counts()
        from apps.guarding.asset_models import (
            GuardAssetDepot,
            GuardAssetType,
            GuardAssetUnit,
            ShiftAssetManifest,
            ShiftAssetManifestLine,
        )

        context["asset_types"] = GuardAssetType.objects.filter(is_active=True).order_by("name")
        context["asset_depots"] = GuardAssetDepot.objects.filter(is_active=True).order_by("name")
        context["available_units"] = GuardAssetUnit.objects.filter(
            status=GuardAssetUnit.Status.AVAILABLE,
        ).select_related("asset_type", "depot")[:500]
        context["shift_manifests"] = (
            ShiftAssetManifest.objects.select_related(
                "assignment__guard",
                "assignment__shift__post",
                "assignment__shift__post__site",
            )
            .prefetch_related("lines__asset_type", "lines__asset_unit")
            .order_by("-created_at")[:100]
        )
        context["manifest_statuses"] = ShiftAssetManifest.Status.choices
        context["manifest_line_statuses"] = ShiftAssetManifestLine.Status.choices
        return context

    def post(self, request):
        from .guarding_asset_console import handle_shifts_asset_action

        action = request.POST.get("action", "shift")
        try:
            if handle_shifts_asset_action(request):
                return redirect("dashboard:guarding-shifts")
            if action == "update_shift":
                shift = get_object_or_404(Shift, pk=request.POST.get("shift_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                next_status = request.POST.get("status") or Shift.Status.PUBLISHED
                shift.post = post
                shift.starts_at = _parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                shift.ends_at = _parse_datetime_field(request.POST.get("ends_at"), label="End time")
                shift.required_guards = _parse_int_field(
                    request.POST.get("required_guards") or 1,
                    label="Required guards",
                    min_value=1,
                )
                shift.notes = request.POST.get("notes", "").strip()
                shift.save(
                    update_fields=[
                        "post",
                        "starts_at",
                        "ends_at",
                        "required_guards",
                        "notes",
                        "updated_at",
                    ]
                )
                existing_guard_ids = set(shift.assignments.values_list("guard_id", flat=True))
                for guard_id in request.POST.getlist("guard_ids"):
                    guard = GuardProfile.objects.filter(pk=guard_id, status=GuardProfile.Status.ACTIVE).first()
                    if guard and guard.pk not in existing_guard_ids:
                        ensure_guard_compliance_ready(guard)
                        ShiftAssignment.objects.get_or_create(shift=shift, guard=guard, defaults={"assigned_by": request.user})
                if next_status != shift.status:
                    transition_shift(shift, next_status)
                messages.success(request, "Shift updated.")
            elif action == "delete_shift":
                shift = get_object_or_404(Shift, pk=request.POST.get("shift_id"))
                shift.delete()
                messages.success(request, "Shift deleted.")
            elif action == "update_assignment":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                note = request.POST.get("notes", "").strip()
                transition_assignment(
                    assignment,
                    request.POST.get("status") or ShiftAssignment.Status.ASSIGNED,
                    note=note,
                )
                if note:
                    assignment.notes = note
                    assignment.save(update_fields=["notes", "updated_at"])
                messages.success(request, "Shift assignment updated.")
            elif action == "delete_assignment":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                assignment.delete()
                messages.success(request, "Shift assignment deleted.")
            elif action == "delete_clock_event":
                event = get_object_or_404(ClockEvent, pk=request.POST.get("clock_event_id"))
                event.delete()
                messages.success(request, "Clock event deleted.")
            elif action == "update_clock_event":
                event = get_object_or_404(ClockEvent, pk=request.POST.get("clock_event_id"))
                event.assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                event.event_type = request.POST.get("event_type") or ClockEvent.EventType.CLOCK_IN
                event.latitude = request.POST.get("latitude") or None
                event.longitude = request.POST.get("longitude") or None
                event.accuracy_m = request.POST.get("accuracy_m") or None
                event.within_geofence = bool(request.POST.get("within_geofence"))
                event.device_timestamp = (
                    _parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None
                )
                event.save()
                messages.success(request, "Clock event updated.")
            elif action == "update_welfare_check":
                check = get_object_or_404(WelfareCheck, pk=request.POST.get("welfare_check_id"))
                check.due_at = _parse_datetime_field(request.POST.get("due_at"), label="Due time")
                check.status = request.POST.get("status") or WelfareCheck.Status.PENDING
                check.response_note = request.POST.get("response_note", "").strip()
                if check.status == WelfareCheck.Status.CONFIRMED and check.responded_at is None:
                    check.responded_at = timezone.now()
                check.save(update_fields=["due_at", "status", "response_note", "responded_at", "updated_at"])
                messages.success(request, "Welfare check updated.")
            elif action == "delete_welfare_check":
                check = get_object_or_404(WelfareCheck, pk=request.POST.get("welfare_check_id"))
                check.delete()
                messages.success(request, "Welfare check deleted.")
            elif action == "clock_event":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                record_clock_event(
                    assignment=assignment,
                    event_type=request.POST.get("event_type") or ClockEvent.EventType.CLOCK_IN,
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    within_geofence=bool(request.POST.get("within_geofence")),
                    device_timestamp=_parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None,
                )
                messages.success(request, "Clock event recorded.")
            elif action == "welfare_check":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                WelfareCheck.objects.create(
                    assignment=assignment,
                    due_at=_parse_datetime_field(request.POST.get("due_at"), label="Due time"),
                    status=request.POST.get("status") or WelfareCheck.Status.PENDING,
                    response_note=request.POST.get("response_note", "").strip(),
                )
                messages.success(request, "Welfare check created.")
            else:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                shift = Shift.objects.create(
                    post=post,
                    starts_at=_parse_datetime_field(request.POST.get("starts_at"), label="Start time"),
                    ends_at=_parse_datetime_field(request.POST.get("ends_at"), label="End time"),
                    status=request.POST.get("status") or Shift.Status.PUBLISHED,
                    required_guards=_parse_int_field(request.POST.get("required_guards") or 1, label="Required guards", min_value=1),
                    notes=request.POST.get("notes", "").strip(),
                    created_by=request.user,
                )
                for guard_id in request.POST.getlist("guard_ids"):
                    guard = GuardProfile.objects.filter(pk=guard_id, status=GuardProfile.Status.ACTIVE).first()
                    if guard:
                        ensure_guard_compliance_ready(guard)
                        ShiftAssignment.objects.get_or_create(shift=shift, guard=guard, defaults={"assigned_by": request.user})
                messages.success(request, "Shift created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-shifts")


class GuardingPatrolsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/patrols.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["checkpoints"] = Checkpoint.objects.select_related("post", "post__site").order_by("post__site__name", "post__name", "name")[:200]
        context["routes"] = PatrolRoute.objects.select_related("post", "post__site").prefetch_related("patrolroutecheckpoint_set__checkpoint").order_by("post__site__name", "name")[:200]
        context["rounds"] = PatrolRound.objects.select_related("route", "assignment", "assignment__guard").prefetch_related("scans").order_by("-scheduled_start")[:200]
        context["scans"] = CheckpointScan.objects.select_related("patrol_round", "checkpoint", "guard").order_by("-scanned_at")[:100]
        context["posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["counts"] = self.get_guarding_counts()
        return context

    def post(self, request):
        action = request.POST.get("action")
        try:
            if action == "update_checkpoint":
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                name = request.POST.get("name", "").strip()
                code = request.POST.get("code", "").strip()
                if not name or not code:
                    raise ValueError("Checkpoint name and code are required.")
                checkpoint.post = post
                checkpoint.name = name
                checkpoint.code = code
                checkpoint.checkpoint_type = request.POST.get("checkpoint_type") or Checkpoint.CheckpointType.QR
                checkpoint.geofence_radius_m = _parse_int_field(
                    request.POST.get("geofence_radius_m") or 50,
                    label="Geofence radius",
                    min_value=1,
                )
                checkpoint.is_active = not bool(request.POST.get("inactive"))
                checkpoint.save(
                    update_fields=[
                        "post",
                        "name",
                        "code",
                        "checkpoint_type",
                        "geofence_radius_m",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Checkpoint updated.")
            elif action == "delete_checkpoint":
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                checkpoint.delete()
                messages.success(request, "Checkpoint deleted.")
            elif action == "update_route":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                name = request.POST.get("name", "").strip()
                if not name:
                    raise ValueError("Route name is required.")
                route.post = post
                route.name = name
                route.expected_duration_minutes = _parse_int_field(
                    request.POST.get("expected_duration_minutes") or 30,
                    label="Expected duration",
                    min_value=1,
                )
                route.is_active = not bool(request.POST.get("inactive"))
                route.save(update_fields=["post", "name", "expected_duration_minutes", "is_active", "updated_at"])
                route.patrolroutecheckpoint_set.all().delete()
                for index, checkpoint_id in enumerate(request.POST.getlist("checkpoint_ids"), start=1):
                    checkpoint = Checkpoint.objects.filter(pk=checkpoint_id, post=post).first()
                    if checkpoint:
                        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=index)
                messages.success(request, "Patrol route updated.")
            elif action == "delete_route":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                route.delete()
                messages.success(request, "Patrol route deleted.")
            elif action == "update_round":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("round_id"))
                next_status = request.POST.get("status") or PatrolRound.Status.SCHEDULED
                patrol_round.route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                patrol_round.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                patrol_round.scheduled_start = _parse_datetime_field(request.POST.get("scheduled_start"), label="Scheduled start")
                patrol_round.scheduled_end = _parse_datetime_field(request.POST.get("scheduled_end"), label="Scheduled end")
                patrol_round.save(
                    update_fields=[
                        "route",
                        "assignment",
                        "scheduled_start",
                        "scheduled_end",
                        "updated_at",
                    ]
                )
                if next_status != patrol_round.status:
                    transition_patrol_round(patrol_round, next_status)
                messages.success(request, "Patrol round updated.")
            elif action == "delete_round":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("round_id"))
                patrol_round.delete()
                messages.success(request, "Patrol round deleted.")
            elif action == "delete_scan":
                scan = get_object_or_404(CheckpointScan, pk=request.POST.get("scan_id"))
                scan.delete()
                messages.success(request, "Checkpoint scan deleted.")
            elif action == "update_scan":
                scan = get_object_or_404(CheckpointScan, pk=request.POST.get("scan_id"))
                scan.patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("patrol_round_id"))
                scan.checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                scan.guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                scan.scanned_at = (
                    _parse_datetime_field(request.POST.get("scanned_at"), label="Scanned time")
                    if request.POST.get("scanned_at")
                    else scan.scanned_at
                )
                scan.latitude = request.POST.get("latitude") or None
                scan.longitude = request.POST.get("longitude") or None
                scan.accuracy_m = request.POST.get("accuracy_m") or None
                scan.within_geofence = bool(request.POST.get("within_geofence"))
                scan.save()
                messages.success(request, "Checkpoint scan updated.")
            elif action == "checkpoint":
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                Checkpoint.objects.create(
                    post=post,
                    name=request.POST.get("name", "").strip(),
                    code=request.POST.get("code", "").strip(),
                    checkpoint_type=request.POST.get("checkpoint_type") or Checkpoint.CheckpointType.QR,
                    geofence_radius_m=_parse_int_field(request.POST.get("geofence_radius_m") or 50, label="Geofence radius", min_value=1),
                )
                messages.success(request, "Checkpoint created.")
            elif action == "route":
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                route = PatrolRoute.objects.create(
                    post=post,
                    name=request.POST.get("name", "").strip(),
                    expected_duration_minutes=_parse_int_field(request.POST.get("expected_duration_minutes") or 30, label="Expected duration", min_value=1),
                )
                for index, checkpoint_id in enumerate(request.POST.getlist("checkpoint_ids"), start=1):
                    checkpoint = Checkpoint.objects.filter(pk=checkpoint_id, post=post).first()
                    if checkpoint:
                        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=index)
                messages.success(request, "Patrol route created.")
            elif action == "round":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                PatrolRound.objects.create(
                    route=route,
                    assignment=assignment,
                    scheduled_start=_parse_datetime_field(request.POST.get("scheduled_start"), label="Scheduled start"),
                    scheduled_end=_parse_datetime_field(request.POST.get("scheduled_end"), label="Scheduled end"),
                )
                messages.success(request, "Patrol round scheduled.")
            elif action == "scan":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("patrol_round_id"))
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                CheckpointScan.objects.create(
                    patrol_round=patrol_round,
                    checkpoint=checkpoint,
                    guard=guard,
                    scanned_at=_parse_datetime_field(request.POST.get("scanned_at"), label="Scanned time")
                    if request.POST.get("scanned_at")
                    else timezone.now(),
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    within_geofence=bool(request.POST.get("within_geofence")),
                )
                if patrol_round.status == PatrolRound.Status.SCHEDULED:
                    transition_patrol_round(patrol_round, PatrolRound.Status.IN_PROGRESS)
                messages.success(request, "Checkpoint scan recorded.")
            else:
                messages.error(request, "Unsupported patrol action.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-patrols")


class GuardingPatrolCompleteView(StaffRequiredMixin, View):
    def post(self, request, round_id):
        patrol_round = get_object_or_404(PatrolRound, pk=round_id)
        try:
            complete_patrol_round(patrol_round)
            messages.success(request, "Patrol round completed.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-patrols")


class GuardingCheckpointQrView(StaffRequiredMixin, View):
    def get(self, request, checkpoint_id):
        import qrcode
        import qrcode.image.svg

        checkpoint = get_object_or_404(Checkpoint.objects.select_related("post", "post__site"), pk=checkpoint_id)
        payload = json.dumps(
            {
                "type": "guard_checkpoint",
                "checkpoint_id": str(checkpoint.id),
                "code": checkpoint.code,
                "site_id": str(checkpoint.post.site_id),
                "site": checkpoint.post.site.name,
                "post_id": str(checkpoint.post_id),
                "post": checkpoint.post.name,
            },
            separators=(",", ":"),
        )
        image = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage)
        response = HttpResponse(content_type="image/svg+xml")
        response["Content-Disposition"] = f'inline; filename="checkpoint-{checkpoint.id}.svg"'
        image.save(response)
        return response


class GuardingPatrolProofExportView(StaffRequiredMixin, View):
    def get(self, request):
        rounds = (
            PatrolRound.objects.select_related(
                "route",
                "route__post",
                "route__post__site",
                "assignment",
                "assignment__guard",
            )
            .prefetch_related("scans__checkpoint", "scans__guard")
            .order_by("-scheduled_start")[:1000]
        )
        rows = []
        for patrol_round in rounds:
            scans = list(patrol_round.scans.all())
            rows.append(
                [
                    patrol_round.id,
                    patrol_round.route.post.site.name,
                    patrol_round.route.post.name,
                    patrol_round.route.name,
                    patrol_round.assignment.guard.full_name if patrol_round.assignment else "",
                    patrol_round.get_status_display(),
                    patrol_round.scheduled_start,
                    patrol_round.scheduled_end,
                    patrol_round.started_at,
                    patrol_round.completed_at,
                    len(scans),
                    "; ".join(
                        f"{scan.checkpoint.name} ({scan.scanned_at:%Y-%m-%d %H:%M})"
                        for scan in sorted(scans, key=lambda item: item.scanned_at)
                    ),
                ]
            )
        if request.GET.get("format") == "pdf" and rounds:
            from django.http import HttpResponse

            from apps.guarding.reports.pdf import render_patrol_round_pdf

            patrol_round = rounds[0]
            pdf_bytes = render_patrol_round_pdf(patrol_round)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="patrol-{patrol_round.id}.pdf"'
            return response

        return _csv_response(
            "guarding-patrol-proof.csv",
            [
                "round_id",
                "site",
                "post",
                "route",
                "guard",
                "status",
                "scheduled_start",
                "scheduled_end",
                "started_at",
                "completed_at",
                "scan_count",
                "scans",
            ],
            rows,
        )


class GuardingReportsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = (
            FieldReport.objects.select_related("site", "post", "guard", "reviewed_by")
            .prefetch_related("attachments")
            .order_by("-submitted_at")[:200]
        )
        context["attachments"] = FieldReportAttachment.objects.select_related("report", "report__guard", "report__site").order_by("-uploaded_at")[:100]
        context["sites"] = Site.objects.order_by("name")
        context["posts"] = GuardPost.objects.select_related("site").order_by("site__name", "name")
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["report_types"] = FieldReport.ReportType.choices
        context["report_statuses"] = FieldReport.Status.choices
        context["counts"] = self.get_guarding_counts()
        return context

    def post(self, request):
        action = request.POST.get("action", "report")
        try:
            if action == "update_report":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                title = request.POST.get("title", "").strip()
                if not title:
                    raise ValueError("Report title is required.")
                report.site = site
                report.post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                report.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                report.guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                report.report_type = request.POST.get("report_type") or FieldReport.ReportType.OTHER
                next_status = request.POST.get("status") or FieldReport.Status.SUBMITTED
                if next_status in {FieldReport.Status.APPROVED, FieldReport.Status.REJECTED} and next_status != report.status:
                    raise ValueError("Use the review action to approve or reject reports.")
                ensure_report_status_transition(report, next_status)
                report.status = next_status
                report.title = title
                report.body = request.POST.get("body", "").strip()
                report.visible_to_client = not bool(request.POST.get("hidden_from_client"))
                report.submitted_at = (
                    _parse_datetime_field(request.POST.get("submitted_at"), label="Submitted time")
                    if request.POST.get("submitted_at")
                    else report.submitted_at
                )
                report.save(
                    update_fields=[
                        "site",
                        "post",
                        "assignment",
                        "guard",
                        "report_type",
                        "status",
                        "title",
                        "body",
                        "visible_to_client",
                        "submitted_at",
                        "updated_at",
                    ]
                )
                messages.success(request, "Field report updated.")
            elif action == "delete_report":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                report.delete()
                messages.success(request, "Field report deleted.")
            elif action == "delete_attachment":
                attachment = get_object_or_404(FieldReportAttachment, pk=request.POST.get("attachment_id"))
                attachment.delete()
                messages.success(request, "Report attachment deleted.")
            elif action == "update_attachment":
                attachment = get_object_or_404(FieldReportAttachment, pk=request.POST.get("attachment_id"))
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                upload = request.FILES.get("file")
                attachment.report = report
                attachment.caption = request.POST.get("caption", "").strip()
                if upload:
                    attachment.file = upload
                    attachment.content_type = getattr(upload, "content_type", "") or attachment.content_type
                attachment.save()
                messages.success(request, "Report attachment updated.")
            elif action == "attachment":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                upload = request.FILES.get("file")
                if not upload:
                    raise ValueError("Attachment file is required.")
                FieldReportAttachment.objects.create(
                    report=report,
                    file=upload,
                    caption=request.POST.get("caption", "").strip(),
                    content_type=getattr(upload, "content_type", "") or "",
                )
                messages.success(request, "Report attachment uploaded.")
            else:
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                FieldReport.objects.create(
                    site=site,
                    post=post,
                    assignment=assignment,
                    guard=guard,
                    report_type=request.POST.get("report_type") or FieldReport.ReportType.OTHER,
                    status=request.POST.get("status")
                    if request.POST.get("status") in {FieldReport.Status.DRAFT, FieldReport.Status.SUBMITTED}
                    else FieldReport.Status.SUBMITTED,
                    title=request.POST.get("title", "").strip(),
                    body=request.POST.get("body", "").strip(),
                    visible_to_client=not bool(request.POST.get("hidden_from_client")),
                    submitted_at=_parse_datetime_field(request.POST.get("submitted_at"), label="Submitted time")
                    if request.POST.get("submitted_at")
                    else timezone.now(),
                )
                messages.success(request, "Field report created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-reports")


class GuardingReportReviewView(StaffRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(FieldReport, pk=report_id)
        try:
            review_field_report(
                report,
                actor=request.user,
                status=request.POST.get("status"),
                note=request.POST.get("note", "").strip(),
            )
            messages.success(request, "Report reviewed.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-reports")


class GuardingReportExportView(StaffRequiredMixin, View):
    def get(self, request):
        reports = (
            FieldReport.objects.select_related("site", "post", "guard", "reviewed_by")
            .order_by("-submitted_at")[:1000]
        )
        rows = [
            [
                report.id,
                report.site.name,
                report.post.name if report.post else "",
                report.guard.full_name if report.guard else "",
                report.get_report_type_display(),
                report.get_status_display(),
                report.title,
                report.body,
                report.visible_to_client,
                report.submitted_at,
                report.reviewed_by.username if report.reviewed_by else "",
                report.reviewed_at or "",
                report.review_note,
            ]
            for report in reports
        ]
        return _csv_response(
            "guarding-reports.csv",
            [
                "report_id",
                "site",
                "post",
                "guard",
                "type",
                "status",
                "title",
                "body",
                "visible_to_client",
                "submitted_at",
                "reviewed_by",
                "reviewed_at",
                "review_note",
            ],
            rows,
        )


class GuardingBackOfficeView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/backoffice.html"
    _BACKOFFICE_ACTION_TABS = {
        "contract": "contracts",
        "update_contract": "contracts",
        "delete_contract": "contracts",
        "availability": "attendance",
        "update_availability": "attendance",
        "delete_availability": "attendance",
        "leave": "attendance",
        "update_leave": "attendance",
        "review_leave": "attendance",
        "delete_leave": "attendance",
        "review_shift_swap": "attendance",
        "delete_shift_swap": "attendance",
        "review_timesheet": "attendance",
        "generate_invoice": "attendance",
        "transition_invoice": "attendance",
        "shift_template": "templates",
        "report_template": "templates",
        "client_access": "templates",
        "training": "people",
        "update_training": "people",
        "delete_training": "people",
        "equipment": "people",
        "update_equipment": "people",
        "delete_equipment": "people",
        "offboarding": "people",
        "update_offboarding": "people",
        "delete_offboarding": "people",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contracts"] = GuardContract.objects.select_related("site", "post").order_by("site__name", "name")[:150]
        context["availability_records"] = GuardAvailability.objects.select_related("guard").order_by("-starts_at")[:150]
        context["leave_requests"] = LeaveRequest.objects.select_related("guard", "reviewed_by").order_by("-starts_at")[:150]
        context["shift_swaps"] = ShiftSwapRequest.objects.select_related("assignment", "assignment__shift", "assignment__shift__post", "requested_by", "target_guard", "reviewed_by").order_by("-created_at")[:150]
        context["timesheets"] = GuardTimesheet.objects.select_related("guard", "site", "post", "assignment").order_by("-period_start")[:150]
        context["invoices"] = GuardInvoice.objects.select_related("site", "contract", "generated_by").order_by("-period_start", "-created_at")[:100]
        context["shift_templates"] = ShiftTemplate.objects.select_related("post", "post__site").order_by("post__site__name", "post__name", "name")[:150]
        context["report_templates"] = ReportTemplate.objects.select_related("site").order_by("report_type", "name")[:150]
        context["client_access"] = ClientPortalAccess.objects.select_related("user", "site").order_by("site__name", "user__username")[:150]
        context["training_records"] = GuardTrainingRecord.objects.select_related("guard").order_by("expires_on", "name")[:150]
        context["equipment_issues"] = GuardEquipmentIssue.objects.select_related("guard", "issued_by").order_by("-issued_at")[:150]
        context["offboarding_checklists"] = GuardOffboardingChecklist.objects.select_related("guard", "completed_by").order_by("-created_at")[:150]
        context["sites"] = Site.objects.order_by("name")
        context["posts"] = GuardPost.objects.select_related("site").order_by("site__name", "name")
        context["guards"] = GuardProfile.objects.order_by("last_name", "first_name")
        context["users"] = User.objects.order_by("username")
        context["assignments"] = ShiftAssignment.objects.select_related("guard", "shift", "shift__post").order_by("-shift__starts_at")[:200]
        context["contract_statuses"] = GuardContract.Status.choices
        context["availability_types"] = GuardAvailability.AvailabilityType.choices
        context["leave_statuses"] = LeaveRequest.Status.choices
        context["swap_statuses"] = ShiftSwapRequest.Status.choices
        context["timesheet_statuses"] = GuardTimesheet.Status.choices
        context["invoice_statuses"] = GuardInvoice.Status.choices
        context["report_types"] = FieldReport.ReportType.choices
        context["client_roles"] = ClientPortalAccess.Role.choices
        context["training_statuses"] = GuardTrainingRecord.Status.choices
        context["equipment_statuses"] = GuardEquipmentIssue.Status.choices
        context["counts"] = self.get_guarding_counts()
        pending_leave = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()
        pending_swaps = ShiftSwapRequest.objects.filter(status=ShiftSwapRequest.Status.PENDING).count()
        pending_timesheets = GuardTimesheet.objects.filter(status=GuardTimesheet.Status.SUBMITTED).count()
        context["backoffice_tab_counts"] = {
            "contracts": GuardContract.objects.count(),
            "pending_leave": pending_leave,
            "pending_swaps": pending_swaps,
            "pending_timesheets": pending_timesheets,
            "attendance_actions": pending_leave + pending_swaps + pending_timesheets,
            "shift_templates": ShiftTemplate.objects.filter(is_active=True).count(),
            "report_templates": ReportTemplate.objects.filter(is_active=True).count(),
            "client_access": ClientPortalAccess.objects.count(),
            "open_offboarding": GuardOffboardingChecklist.objects.exclude(
                equipment_returned=True,
                documents_archived=True,
                access_revoked=True,
                final_timesheet_approved=True,
            ).count(),
        }
        return context

    def post(self, request):
        action = request.POST.get("action", "")
        try:
            if action in {"contract", "update_contract"}:
                contract = (
                    get_object_or_404(GuardContract, pk=request.POST.get("contract_id"))
                    if action == "update_contract"
                    else GuardContract()
                )
                contract.site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                contract.post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                contract.name = request.POST.get("name", "").strip()
                if not contract.name:
                    raise ValueError("Contract name is required.")
                contract.status = request.POST.get("status") or GuardContract.Status.DRAFT
                contract.starts_on = _parse_date_field(request.POST.get("starts_on"), label="Start date")
                contract.ends_on = _parse_date_field(request.POST.get("ends_on"), label="End date") if request.POST.get("ends_on") else None
                contract.bill_rate = _parse_decimal_field(request.POST.get("bill_rate", "0"), label="Bill rate", min_value=Decimal("0.00"))
                contract.pay_rate = _parse_decimal_field(request.POST.get("pay_rate", "0"), label="Pay rate", min_value=Decimal("0.00"))
                contract.overtime_multiplier = _parse_decimal_field(
                    request.POST.get("overtime_multiplier", "1.5"),
                    label="Overtime multiplier",
                    min_value=Decimal("1.00"),
                )
                contract.sla_minutes = _parse_int_field(request.POST.get("sla_minutes", "30"), label="SLA minutes", min_value=1)
                contract.notes = request.POST.get("notes", "").strip()
                contract.full_clean()
                contract.save()
                messages.success(request, "Contract saved.")
            elif action == "delete_contract":
                get_object_or_404(GuardContract, pk=request.POST.get("contract_id")).delete()
                messages.success(request, "Contract deleted.")
            elif action in {"availability", "update_availability"}:
                availability = (
                    get_object_or_404(GuardAvailability, pk=request.POST.get("availability_id"))
                    if action == "update_availability"
                    else GuardAvailability(created_by=request.user)
                )
                availability.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                availability.availability_type = request.POST.get("availability_type") or GuardAvailability.AvailabilityType.UNAVAILABLE
                availability.starts_at = _parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                availability.ends_at = _parse_datetime_field(request.POST.get("ends_at"), label="End time")
                availability.reason = request.POST.get("reason", "").strip()
                availability.full_clean()
                availability.save()
                messages.success(request, "Availability saved.")
            elif action == "delete_availability":
                get_object_or_404(GuardAvailability, pk=request.POST.get("availability_id")).delete()
                messages.success(request, "Availability deleted.")
            elif action in {"leave", "update_leave"}:
                leave = get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id")) if action == "update_leave" else LeaveRequest()
                leave.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                leave.starts_at = _parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                leave.ends_at = _parse_datetime_field(request.POST.get("ends_at"), label="End time")
                leave.reason = request.POST.get("reason", "").strip()
                if request.POST.get("status"):
                    leave.status = request.POST.get("status")
                leave.full_clean()
                leave.save()
                messages.success(request, "Leave request saved.")
            elif action == "review_leave":
                leave = get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id"))
                review_leave_request(
                    leave,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Leave request reviewed.")
            elif action == "delete_leave":
                get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id")).delete()
                messages.success(request, "Leave request deleted.")
            elif action == "review_shift_swap":
                swap = get_object_or_404(ShiftSwapRequest, pk=request.POST.get("swap_id"))
                review_shift_swap_request(
                    swap,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Shift swap reviewed.")
            elif action == "delete_shift_swap":
                get_object_or_404(ShiftSwapRequest, pk=request.POST.get("swap_id")).delete()
                messages.success(request, "Shift swap deleted.")
            elif action == "review_timesheet":
                timesheet = get_object_or_404(GuardTimesheet, pk=request.POST.get("timesheet_id"))
                review_timesheet(
                    timesheet,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Timesheet updated.")
            elif action == "delete_timesheet":
                get_object_or_404(GuardTimesheet, pk=request.POST.get("timesheet_id")).delete()
                messages.success(request, "Timesheet deleted.")
            elif action == "generate_invoice":
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                contract = GuardContract.objects.filter(pk=request.POST.get("contract_id"), site=site).first()
                invoice = generate_guard_invoice(
                    site=site,
                    contract=contract,
                    period_start=_parse_date_field(request.POST.get("period_start"), label="Period start"),
                    period_end=_parse_date_field(request.POST.get("period_end"), label="Period end"),
                    actor=request.user,
                )
                messages.success(request, f"Invoice {invoice.invoice_number} generated.")
            elif action == "transition_invoice":
                invoice = get_object_or_404(GuardInvoice, pk=request.POST.get("invoice_id"))
                transition_guard_invoice(invoice, status=request.POST.get("status"), actor=request.user)
                messages.success(request, "Invoice updated.")
            elif action == "delete_invoice":
                get_object_or_404(GuardInvoice, pk=request.POST.get("invoice_id")).delete()
                messages.success(request, "Invoice deleted.")
            elif action in {"shift_template", "update_shift_template"}:
                shift_template = (
                    get_object_or_404(ShiftTemplate, pk=request.POST.get("shift_template_id"))
                    if action == "update_shift_template"
                    else ShiftTemplate()
                )
                shift_template.post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                shift_template.name = request.POST.get("name", "").strip()
                if not shift_template.name:
                    raise ValueError("Shift template name is required.")
                shift_template.start_time = _parse_time_field(request.POST.get("start_time"), label="Start time")
                shift_template.end_time = _parse_time_field(request.POST.get("end_time"), label="End time")
                shift_template.required_guards = _parse_int_field(request.POST.get("required_guards", "1"), label="Required guards", min_value=1)
                shift_template.days_of_week = [day for day in request.POST.getlist("days_of_week") if day]
                shift_template.is_active = bool(request.POST.get("is_active"))
                shift_template.notes = request.POST.get("notes", "").strip()
                shift_template.full_clean()
                shift_template.save()
                messages.success(request, "Shift template saved.")
            elif action == "delete_shift_template":
                get_object_or_404(ShiftTemplate, pk=request.POST.get("shift_template_id")).delete()
                messages.success(request, "Shift template deleted.")
            elif action in {"report_template", "update_report_template"}:
                template = (
                    get_object_or_404(ReportTemplate, pk=request.POST.get("template_id"))
                    if action == "update_report_template"
                    else ReportTemplate(created_by=request.user)
                )
                template.name = request.POST.get("name", "").strip()
                if not template.name:
                    raise ValueError("Template name is required.")
                template.report_type = request.POST.get("report_type") or FieldReport.ReportType.OTHER
                template.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                template.is_active = bool(request.POST.get("is_active"))
                template.schema = {"fields": [field.strip() for field in request.POST.get("fields", "").splitlines() if field.strip()]}
                template.save()
                messages.success(request, "Report template saved.")
            elif action == "delete_report_template":
                get_object_or_404(ReportTemplate, pk=request.POST.get("template_id")).delete()
                messages.success(request, "Report template deleted.")
            elif action in {"client_access", "update_client_access"}:
                access = (
                    get_object_or_404(ClientPortalAccess, pk=request.POST.get("access_id"))
                    if action == "update_client_access"
                    else ClientPortalAccess()
                )
                access.user = get_object_or_404(User, pk=request.POST.get("user_id"))
                access.site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                access.role = request.POST.get("role") or ClientPortalAccess.Role.VIEWER
                access.can_view_reports = bool(request.POST.get("can_view_reports"))
                access.can_view_patrols = bool(request.POST.get("can_view_patrols"))
                access.can_view_attendance = bool(request.POST.get("can_view_attendance"))
                access.can_acknowledge_reports = bool(request.POST.get("can_acknowledge_reports"))
                access.full_clean()
                access.save()
                messages.success(request, "Client access saved.")
            elif action == "delete_client_access":
                get_object_or_404(ClientPortalAccess, pk=request.POST.get("access_id")).delete()
                messages.success(request, "Client access deleted.")
            elif action in {"training", "update_training"}:
                training = (
                    get_object_or_404(GuardTrainingRecord, pk=request.POST.get("training_id"))
                    if action == "update_training"
                    else GuardTrainingRecord()
                )
                training.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                training.name = request.POST.get("name", "").strip()
                if not training.name:
                    raise ValueError("Training name is required.")
                training.provider = request.POST.get("provider", "").strip()
                training.status = request.POST.get("status") or GuardTrainingRecord.Status.PLANNED
                training.completed_on = _parse_date_field(request.POST.get("completed_on"), label="Completed date") if request.POST.get("completed_on") else None
                training.expires_on = _parse_date_field(request.POST.get("expires_on"), label="Expiry date") if request.POST.get("expires_on") else None
                training.certificate_number = request.POST.get("certificate_number", "").strip()
                training.notes = request.POST.get("notes", "").strip()
                training.save()
                messages.success(request, "Training record saved.")
            elif action == "delete_training":
                get_object_or_404(GuardTrainingRecord, pk=request.POST.get("training_id")).delete()
                messages.success(request, "Training record deleted.")
            elif action in {"equipment", "update_equipment"}:
                equipment = (
                    get_object_or_404(GuardEquipmentIssue, pk=request.POST.get("equipment_id"))
                    if action == "update_equipment"
                    else GuardEquipmentIssue(issued_by=request.user)
                )
                equipment.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                equipment.item_name = request.POST.get("item_name", "").strip()
                if not equipment.item_name:
                    raise ValueError("Equipment item name is required.")
                equipment.item_code = request.POST.get("item_code", "").strip()
                equipment.quantity = _parse_int_field(request.POST.get("quantity", "1"), label="Quantity", min_value=1)
                equipment.status = request.POST.get("status") or GuardEquipmentIssue.Status.ISSUED
                equipment.issued_at = _parse_datetime_field(request.POST.get("issued_at"), label="Issued time") if request.POST.get("issued_at") else equipment.issued_at
                equipment.returned_at = _parse_datetime_field(request.POST.get("returned_at"), label="Returned time") if request.POST.get("returned_at") else None
                equipment.notes = request.POST.get("notes", "").strip()
                equipment.save()
                from apps.guarding.asset_services import sync_offboarding_equipment_flag

                sync_offboarding_equipment_flag(equipment.guard)
                messages.success(request, "Equipment issue saved.")
            elif action == "delete_equipment":
                get_object_or_404(GuardEquipmentIssue, pk=request.POST.get("equipment_id")).delete()
                messages.success(request, "Equipment issue deleted.")
            elif action in {"offboarding", "update_offboarding"}:
                checklist = (
                    get_object_or_404(GuardOffboardingChecklist, pk=request.POST.get("offboarding_id"))
                    if action == "update_offboarding"
                    else GuardOffboardingChecklist()
                )
                checklist.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                checklist.equipment_returned = bool(request.POST.get("equipment_returned"))
                checklist.documents_archived = bool(request.POST.get("documents_archived"))
                checklist.access_revoked = bool(request.POST.get("access_revoked"))
                checklist.final_timesheet_approved = bool(request.POST.get("final_timesheet_approved"))
                checklist.exit_notes = request.POST.get("exit_notes", "").strip()
                if checklist.is_complete and checklist.completed_at is None:
                    checklist.completed_by = request.user
                    checklist.completed_at = timezone.now()
                checklist.save()
                messages.success(request, "Offboarding checklist saved.")
            elif action == "delete_offboarding":
                get_object_or_404(GuardOffboardingChecklist, pk=request.POST.get("offboarding_id")).delete()
                messages.success(request, "Offboarding checklist deleted.")
        except Exception as exc:
            messages.error(request, str(exc))
        tab = self._BACKOFFICE_ACTION_TABS.get(action)
        if tab:
            return redirect(f"{reverse('dashboard:guarding-backoffice')}?tab={tab}")
        return redirect("dashboard:guarding-backoffice")


class GuardingTimesheetExportView(StaffRequiredMixin, View):
    def get(self, request):
        timesheets = (
            GuardTimesheet.objects.select_related("guard", "site", "post", "assignment")
            .order_by("-period_start")[:1000]
        )
        rows = [
            [
                sheet.id,
                sheet.guard.full_name,
                sheet.site.name,
                sheet.post.name if sheet.post else "",
                sheet.period_start,
                sheet.period_end,
                sheet.regular_minutes,
                sheet.overtime_minutes,
                sheet.total_minutes,
                sheet.pay_amount,
                sheet.bill_amount,
                sheet.get_status_display(),
                sheet.approved_by.username if sheet.approved_by else "",
                sheet.approved_at or "",
                sheet.export_reference,
            ]
            for sheet in timesheets
        ]
        return _csv_response(
            "guarding-timesheets.csv",
            [
                "timesheet_id",
                "guard",
                "site",
                "post",
                "period_start",
                "period_end",
                "regular_minutes",
                "overtime_minutes",
                "total_minutes",
                "pay_amount",
                "bill_amount",
                "status",
                "approved_by",
                "approved_at",
                "export_reference",
            ],
            rows,
        )


class GuardingClientPortalView(GuardingClientRequiredMixin, TemplateView):
    template_name = "dashboard/guarding/client.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access_records = list(ClientPortalAccess.objects.select_related("site").filter(user=self.request.user))
        site_ids = [access.site_id for access in access_records]
        report_site_ids = [access.site_id for access in access_records if access.can_view_reports]
        acknowledge_site_ids = [access.site_id for access in access_records if access.can_acknowledge_reports]
        patrol_site_ids = [access.site_id for access in access_records if access.can_view_patrols]
        attendance_site_ids = [access.site_id for access in access_records if access.can_view_attendance]
        reports = (
            FieldReport.objects.select_related("site", "post", "guard")
            .prefetch_related("client_acknowledgements")
            .filter(
                site_id__in=report_site_ids,
                visible_to_client=True,
                status=FieldReport.Status.APPROVED,
            )
            .order_by("-submitted_at")[:100]
        )
        patrol_rounds = (
            PatrolRound.objects.select_related(
                "route",
                "route__post",
                "route__post__site",
                "assignment",
                "assignment__guard",
            )
            .prefetch_related("scans")
            .filter(route__post__site_id__in=patrol_site_ids)
            .order_by("-scheduled_start")[:100]
        )
        assignments = (
            ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
            .filter(shift__post__site_id__in=attendance_site_ids)
            .order_by("-shift__starts_at")[:100]
        )
        timesheets = (
            GuardTimesheet.objects.select_related("guard", "site", "post")
            .filter(
                site_id__in=attendance_site_ids,
                status__in=[
                    GuardTimesheet.Status.SUBMITTED,
                    GuardTimesheet.Status.APPROVED,
                    GuardTimesheet.Status.EXPORTED,
                ],
            )
            .order_by("-period_start")[:100]
        )
        context.update(
            {
                "access_records": access_records,
                "sites": Site.objects.filter(id__in=site_ids).order_by("name"),
                "reports": reports,
                "patrol_rounds": patrol_rounds,
                "assignments": assignments,
                "timesheets": timesheets,
                "can_export_reports": bool(report_site_ids),
                "acknowledge_site_ids": acknowledge_site_ids,
                "client_counts": {
                    "sites": len(site_ids),
                    "reports": reports.count(),
                    "patrols": patrol_rounds.count(),
                    "assignments": assignments.count(),
                },
            }
        )
        return context


class GuardingClientReportAcknowledgeView(GuardingClientRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(FieldReport, pk=report_id)
        try:
            acknowledge_field_report(report, user=request.user, comment=request.POST.get("comment", "").strip())
            messages.success(request, "Report acknowledged.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:client-guarding")


class GuardingClientReportExportView(GuardingClientRequiredMixin, View):
    def get(self, request):
        report_site_ids = ClientPortalAccess.objects.filter(
            user=request.user,
            can_view_reports=True,
        ).values_list("site_id", flat=True)
        reports = (
            FieldReport.objects.select_related("site", "post", "guard")
            .filter(
                site_id__in=report_site_ids,
                visible_to_client=True,
                status=FieldReport.Status.APPROVED,
            )
            .order_by("-submitted_at")[:1000]
        )
        rows = [
            [
                report.site.name,
                report.post.name if report.post else "",
                report.guard.full_name if report.guard else "",
                report.get_report_type_display(),
                report.title,
                report.body,
                report.submitted_at,
            ]
            for report in reports
        ]
        return _csv_response(
            "guarding-client-reports.csv",
            ["site", "post", "guard", "type", "title", "body", "submitted_at"],
            rows,
        )


class GuardingLiveMapView(StaffRequiredMixin, View):
    """Legacy route — field guards live on the global map."""

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('dashboard:site-map')}?focus=guards")


class GuardingAnalyticsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/analytics.html"

    def get_context_data(self, **kwargs):
        from apps.guarding.analytics import guarding_kpis

        context = super().get_context_data(**kwargs)
        days = int(self.request.GET.get("days", 7))
        context["kpis"] = guarding_kpis(days=days)
        context["days"] = days
        context["counts"] = self.get_guarding_counts()
        return context


class GuardingDispatchView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/dispatch.html"
    _DISPATCH_ACTION_TABS = {
        "save_dispatch_policy": "policies",
        "panic_alert": "sos",
        "update_panic_alert": "sos",
        "delete_panic_alert": "sos",
        "update_task": "tasks",
        "delete_task": "tasks",
        "task": "tasks",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["panic_alerts"] = GuardPanicAlert.objects.select_related("guard", "site", "assignment").order_by("-created_at")[:100]
        context["dispatch_tasks"] = DispatchTask.objects.select_related("site", "assigned_guard", "panic_alert").order_by("-created_at")[:200]
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["sites"] = Site.objects.order_by("name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["priorities"] = DispatchTask.Priority.choices
        context["panic_statuses"] = GuardPanicAlert.Status.choices
        policies = {
            policy.site_id: policy
            for policy in SiteGuardDispatchPolicy.objects.select_related("site")
        }
        context["site_dispatch_policies"] = [
            {"site": site, "policy": policies.get(site.id)}
            for site in Site.objects.order_by("name")
        ]
        context["alarm_severity_options"] = [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ]
        context["counts"] = self.get_guarding_counts()
        counts = context["counts"]
        context["dispatch_tab_counts"] = {
            "open_panic": counts["open_panic"],
            "open_tasks": counts["open_dispatch"],
            "policy_sites": len(context["site_dispatch_policies"]),
            "active_policies": SiteGuardDispatchPolicy.objects.filter(is_active=True).count(),
        }
        return context

    def post(self, request):
        try:
            action = request.POST.get("action", "task")
            if action == "save_dispatch_policy":
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                policy, _ = SiteGuardDispatchPolicy.objects.get_or_create(site=site)
                policy.is_active = bool(request.POST.get("is_active"))
                policy.auto_from_emergency = bool(request.POST.get("auto_from_emergency"))
                policy.auto_from_alarm = bool(request.POST.get("auto_from_alarm"))
                policy.auto_assign_nearest = bool(request.POST.get("auto_assign_nearest"))
                policy.default_priority = (
                    request.POST.get("default_priority") or DispatchTask.Priority.HIGH
                )
                policy.alarm_severities = [
                    value for value in request.POST.getlist("alarm_severities") if value
                ]
                policy.full_clean()
                policy.save()
                messages.success(request, f"Auto-dispatch policy saved for {site.name}.")
            elif action == "panic_alert":
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                if site is None and assignment:
                    site = assignment.shift.post.site
                GuardPanicAlert.objects.create(
                    guard=guard,
                    assignment=assignment,
                    site=site,
                    status=GuardPanicAlert.Status.OPEN,
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Panic alert created.")
            elif action == "update_panic_alert":
                alert = get_object_or_404(GuardPanicAlert, pk=request.POST.get("alert_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                next_status = request.POST.get("status") or GuardPanicAlert.Status.OPEN
                if next_status != alert.status:
                    ensure_panic_alert_status_transition(alert, next_status)
                alert.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                alert.assignment = assignment
                alert.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                alert.latitude = request.POST.get("latitude") or None
                alert.longitude = request.POST.get("longitude") or None
                alert.accuracy_m = request.POST.get("accuracy_m") or None
                alert.note = request.POST.get("note", "").strip()
                alert.save(update_fields=["guard", "assignment", "site", "latitude", "longitude", "accuracy_m", "note", "updated_at"])
                if next_status != alert.status:
                    transition_panic_alert(alert, status=next_status, actor=request.user)
                messages.success(request, "Panic alert updated.")
            elif action == "delete_panic_alert":
                alert = get_object_or_404(GuardPanicAlert, pk=request.POST.get("alert_id"))
                alert.delete()
                messages.success(request, "Panic alert deleted.")
            elif action == "update_task":
                task = get_object_or_404(DispatchTask, pk=request.POST.get("task_id"))
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                title = request.POST.get("title", "").strip()
                if not title:
                    raise ValueError("Dispatch title is required.")
                was_unassigned = task.assigned_guard_id is None
                task.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                task.assigned_guard = guard
                task.priority = request.POST.get("priority") or DispatchTask.Priority.MEDIUM
                task.title = title
                task.description = request.POST.get("description", "").strip()
                if guard and was_unassigned:
                    task.assigned_at = timezone.now()
                task.save(
                    update_fields=[
                        "site",
                        "assigned_guard",
                        "priority",
                        "title",
                        "description",
                        "assigned_at",
                        "updated_at",
                    ]
                )
                messages.success(request, "Dispatch task updated.")
            elif action == "delete_task":
                task = get_object_or_404(DispatchTask, pk=request.POST.get("task_id"))
                task.delete()
                messages.success(request, "Dispatch task deleted.")
            else:
                site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                DispatchTask.objects.create(
                    site=site,
                    assigned_guard=guard,
                    assigned_at=timezone.now() if guard else None,
                    status=DispatchTask.Status.ASSIGNED if guard else DispatchTask.Status.OPEN,
                    priority=request.POST.get("priority") or DispatchTask.Priority.MEDIUM,
                    title=request.POST.get("title", "").strip(),
                    description=request.POST.get("description", "").strip(),
                    created_by=request.user,
                )
                messages.success(request, "Dispatch task created.")
        except Exception as exc:
            messages.error(request, str(exc))
        tab = self._DISPATCH_ACTION_TABS.get(action)
        if tab:
            return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab={tab}")
        return redirect("dashboard:guarding-dispatch")


class GuardingPanicActionView(StaffRequiredMixin, View):
    def post(self, request, alert_id, action):
        alert = get_object_or_404(GuardPanicAlert, pk=alert_id)
        try:
            if action == "acknowledge":
                acknowledge_panic_alert(alert, actor=request.user)
            elif action == "resolve":
                resolve_panic_alert(alert, actor=request.user)
            else:
                messages.error(request, "Unsupported panic action.")
                return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=sos")
            messages.success(request, "Panic alert updated.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=sos")


class GuardingDispatchActionView(StaffRequiredMixin, View):
    action_statuses = {
        "assign": DispatchTask.Status.ASSIGNED,
        "accept": DispatchTask.Status.ACCEPTED,
        "en-route": DispatchTask.Status.EN_ROUTE,
        "arrive": DispatchTask.Status.ARRIVED,
        "resolve": DispatchTask.Status.RESOLVED,
        "cancel": DispatchTask.Status.CANCELLED,
    }

    def post(self, request, task_id, action):
        task = get_object_or_404(DispatchTask, pk=task_id)
        if action not in self.action_statuses:
            messages.error(request, "Unsupported dispatch action.")
            return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=tasks")
        guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
        if guard:
            task.assigned_guard = guard
            task.save(update_fields=["assigned_guard", "updated_at"])
        try:
            transition_dispatch_task(
                task,
                status=self.action_statuses[action],
                actor=request.user,
                note=request.POST.get("note", "").strip(),
            )
            messages.success(request, "Dispatch task updated.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=tasks")


class EmergencyServiceManagementView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/emergency/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_statuses = [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]
        site_services = SiteEmergencyService.objects.select_related("site", "plan").order_by("site__name")
        account_services = AccountEmergencyService.objects.select_related("user", "plan").order_by("user__username")
        context["plans"] = EmergencyServicePlan.objects.all()
        context["active_plans"] = EmergencyServicePlan.objects.filter(is_active=True).order_by("monthly_rate")
        context["site_services"] = site_services
        context["account_services"] = account_services
        context["available_sites"] = Site.objects.filter(emergency_service__isnull=True).order_by("name")
        context["available_customers"] = User.objects.filter(
            is_staff=False,
            emergency_service__isnull=True,
        ).order_by("username")
        context["statuses"] = EmergencyServiceStatus.choices
        context["site_mrr"] = (
            SiteEmergencyService.objects.filter(status__in=active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["account_mrr"] = (
            AccountEmergencyService.objects.filter(status__in=active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["total_emergency_mrr"] = context["site_mrr"] + context["account_mrr"]
        context["active_site_count"] = SiteEmergencyService.objects.filter(status__in=active_statuses).count()
        context["active_account_count"] = AccountEmergencyService.objects.filter(status__in=active_statuses).count()
        return context


class CreateEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        rate = request.POST.get("monthly_rate", "").strip()
        if not name or not rate:
            messages.error(request, "Plan name and monthly rate are required.")
            return redirect("dashboard:emergency-services")
        try:
            parsed_rate = _parse_decimal_field(rate, label="Monthly rate", min_value=Decimal("0.00"))
            EmergencyServicePlan.objects.create(
                name=name,
                monthly_rate=parsed_rate,
                description=request.POST.get("description", "").strip(),
                is_active=request.POST.get("is_active", "1") == "1",
            )
            messages.success(request, f"Emergency plan '{name}' created.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class UpdateEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request, plan_id):
        plan = get_object_or_404(EmergencyServicePlan, pk=plan_id)
        name = request.POST.get("name", "").strip()
        rate = request.POST.get("monthly_rate", "").strip()
        if not name or not rate:
            messages.error(request, "Plan name and monthly rate are required.")
            return redirect("dashboard:emergency-services")
        try:
            plan.name = name
            plan.monthly_rate = _parse_decimal_field(rate, label="Monthly rate", min_value=Decimal("0.00"))
            plan.description = request.POST.get("description", "").strip()
            plan.is_active = request.POST.get("is_active") == "1"
            plan.save(update_fields=["name", "monthly_rate", "description", "is_active"])
            messages.success(request, f"Emergency plan '{plan.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request, plan_id):
        plan = get_object_or_404(EmergencyServicePlan, pk=plan_id)
        if plan.site_services.exists() or plan.account_services.exists():
            messages.error(request, f"Cannot delete '{plan.name}' while it is linked to emergency services.")
            return redirect("dashboard:emergency-services")
        name = plan.name
        plan.delete()
        messages.success(request, f"Emergency plan '{name}' deleted.")
        return redirect("dashboard:emergency-services")


def _parse_emergency_service_payload(request):
    plan_id = request.POST.get("plan_id", "").strip()
    plan = EmergencyServicePlan.objects.filter(pk=plan_id).first() if plan_id else None
    monthly_rate = request.POST.get("monthly_rate", "").strip()
    if not monthly_rate and plan:
        monthly_rate = str(plan.monthly_rate)
    if not monthly_rate:
        raise ValueError("Monthly rate is required.")
    status = request.POST.get("status", EmergencyServiceStatus.ACTIVE).strip()
    valid_statuses = {choice[0] for choice in EmergencyServiceStatus.choices}
    if status not in valid_statuses:
        raise ValueError("Please choose a valid emergency service status.")
    next_due_date = request.POST.get("next_due_date", "").strip()
    return {
        "plan": plan,
        "monthly_rate": _parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00")),
        "status": status,
        "next_due_date": _parse_date_field(next_due_date, label="Next due date") if next_due_date else None,
        "notes": request.POST.get("notes", "").strip(),
    }


class CreateSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request):
        site = get_object_or_404(Site, pk=request.POST.get("site_id"))
        if SiteEmergencyService.objects.filter(site=site).exists():
            messages.error(request, f"'{site.name}' already has emergency service configured.")
            return redirect("dashboard:emergency-services")
        try:
            SiteEmergencyService.objects.create(site=site, **_parse_emergency_service_payload(request))
            messages.success(request, f"Emergency service enabled for '{site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class CreateAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request):
        user = get_object_or_404(User, pk=request.POST.get("user_id"), is_staff=False)
        if AccountEmergencyService.objects.filter(user=user).exists():
            messages.error(request, f"'{user.username}' already has account emergency service configured.")
            return redirect("dashboard:emergency-services")
        try:
            AccountEmergencyService.objects.create(user=user, **_parse_emergency_service_payload(request))
            messages.success(request, f"Emergency service enabled for '{user.username}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class UpdateSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(SiteEmergencyService, pk=service_id)
        try:
            for field, value in _parse_emergency_service_payload(request).items():
                setattr(service, field, value)
            service.save(update_fields=["plan", "monthly_rate", "status", "next_due_date", "notes", "updated_at"])
            messages.success(request, f"Updated emergency service for '{service.site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(SiteEmergencyService.objects.select_related("site"), pk=service_id)
        site_name = service.site.name
        service.delete()
        messages.success(request, f"Emergency service removed from '{site_name}'.")
        return redirect("dashboard:emergency-services")


class UpdateAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(AccountEmergencyService, pk=service_id)
        try:
            for field, value in _parse_emergency_service_payload(request).items():
                setattr(service, field, value)
            service.save(update_fields=["plan", "monthly_rate", "status", "next_due_date", "notes", "updated_at"])
            messages.success(request, f"Updated emergency service for '{service.user.username}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(AccountEmergencyService.objects.select_related("user"), pk=service_id)
        username = service.user.username
        service.delete()
        messages.success(request, f"Emergency service removed from '{username}'.")
        return redirect("dashboard:emergency-services")

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
        zones = OperationsZone.objects.annotate(site_count=Count("sites")).order_by("sort_order", "name")
        return render(request, self.template_name, {"zones": zones})

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
        if _operations_zone_name_taken(name):
            messages.error(request, f"A zone named '{name}' already exists.")
            return redirect("dashboard:map-zones")
        OperationsZone.objects.create(
            name=name,
            color=_normalize_zone_color(color),
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
        if _operations_zone_name_taken(name, exclude_pk=zone.pk):
            messages.error(request, f"A zone named '{name}' already exists.")
            return redirect("dashboard:map-zones")
        zone.name = name
        zone.color = _normalize_zone_color(color)
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
            _assign_site_operations_zone(site, request.POST.get("operations_zone", ""))
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
                "operations_zones": _operations_zones_for_site(site),
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
        _assign_site_operations_zone(site, request.POST.get("operations_zone", ""))
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
    template_name = "dashboard/billing/subscriptions.html"
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
        emergency_active_statuses = [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]
        context["emergency_site_mrr"] = (
            SiteEmergencyService.objects.filter(status__in=emergency_active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["emergency_account_mrr"] = (
            AccountEmergencyService.objects.filter(status__in=emergency_active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["emergency_total_mrr"] = context["emergency_site_mrr"] + context["emergency_account_mrr"]
        context["combined_mrr"] = context["total_mrr"] + context["emergency_total_mrr"]
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
            try:
                emergency_service = sub.site.emergency_service
            except SiteEmergencyService.DoesNotExist:
                emergency_service = None
            setattr(sub, "emergency_service", emergency_service)
        pkgs = SubscriptionPackage.objects.filter(is_active=True).order_by("monthly_rate")
        context["packages"] = pkgs
        context["packages_json"] = json.dumps([
            {
                "id": str(p.id),
                "rate": str(p.monthly_rate),
                "grace": p.grace_period_days,
                "emergency": p.includes_emergency_service,
                "emergencyRate": str(p.emergency_monthly_rate),
            }
            for p in pkgs
        ])
        context["emergency_statuses"] = EmergencyServiceStatus.choices
        context["active_emergency_plans"] = EmergencyServicePlan.objects.filter(is_active=True).order_by("monthly_rate")
        return context


def _sync_site_emergency_addon_from_subscription_request(request, *, site, subscription_status):
    enabled = request.POST.get("emergency_enabled") == "1"
    existing = SiteEmergencyService.objects.filter(site=site).first()
    if not enabled:
        if existing:
            existing.status = EmergencyServiceStatus.CANCELLED
            existing.save(update_fields=["status", "updated_at"])
        return existing

    emergency_rate = request.POST.get("emergency_monthly_rate", "").strip()
    if not emergency_rate:
        raise ValueError("Emergency add-on rate is required when patrol support is enabled.")
    status = request.POST.get("emergency_status", "").strip() or subscription_status
    valid_statuses = {choice[0] for choice in EmergencyServiceStatus.choices}
    if status not in valid_statuses:
        raise ValueError("Please choose a valid emergency add-on status.")
    parsed_rate = _parse_decimal_field(
        emergency_rate,
        label="Emergency add-on rate",
        min_value=Decimal("0.00"),
    )
    defaults = {
        "monthly_rate": parsed_rate,
        "status": status,
        "next_due_date": _parse_date_field(request.POST.get("next_due_date", ""), label="Next due date"),
        "notes": request.POST.get("emergency_notes", "").strip(),
    }
    service, _ = SiteEmergencyService.objects.update_or_create(site=site, defaults=defaults)
    return service


def _sync_site_emergency_addon_lifecycle(subscription, *, next_due_date=None, status=None):
    service = SiteEmergencyService.objects.filter(site=subscription.site).first()
    if service is None:
        return None
    update_fields = ["updated_at"]
    if next_due_date is not None:
        service.next_due_date = next_due_date
        update_fields.append("next_due_date")
    if status is not None:
        service.status = status
        update_fields.append("status")
    service.save(update_fields=update_fields)
    return service


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
            subscription = Subscription.objects.create(
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
            _sync_site_emergency_addon_from_subscription_request(
                request,
                site=site,
                subscription_status=subscription.status,
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
            _sync_site_emergency_addon_from_subscription_request(
                request,
                site=sub.site,
                subscription_status=sub.status,
            )
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
            _sync_site_emergency_addon_lifecycle(
                sub,
                next_due_date=new_due,
                status=EmergencyServiceStatus.ACTIVE if sub.status == Subscription.STATUS_ACTIVE else sub.status,
            )
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
            _sync_site_emergency_addon_lifecycle(sub, status=EmergencyServiceStatus.SUSPENDED)
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
        _sync_site_emergency_addon_lifecycle(sub, status=EmergencyServiceStatus.CANCELLED)
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
        _sync_site_emergency_addon_lifecycle(
            sub,
            next_due_date=sub.next_due_date,
            status=EmergencyServiceStatus.ACTIVE,
        )
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
    template_name = "dashboard/billing/packages.html"

    def get(self, request):
        packages = SubscriptionPackage.objects.all()
        emergency_mrr = (
            SiteEmergencyService.objects.filter(status__in=[EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE])
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        return render(
            request,
            self.template_name,
            {"packages": packages, "emergency_mrr": emergency_mrr},
        )

    def post(self, request):
        name = request.POST.get("name", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        grace_period_days = request.POST.get("grace_period_days", "7").strip()
        description = request.POST.get("description", "").strip()
        includes_emergency = request.POST.get("includes_emergency_service") == "on"
        emergency_rate = request.POST.get("emergency_monthly_rate", "0").strip() or "0"

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            parsed_rate = _parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            parsed_grace = _parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            parsed_emergency_rate = _parse_decimal_field(emergency_rate, label="Emergency add-on rate", min_value=Decimal("0.00"))
            SubscriptionPackage.objects.create(
                name=name,
                monthly_rate=parsed_rate,
                includes_emergency_service=includes_emergency,
                emergency_monthly_rate=parsed_emergency_rate,
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
        includes_emergency = request.POST.get("includes_emergency_service") == "on"
        emergency_rate = request.POST.get("emergency_monthly_rate", "0").strip() or "0"

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            pkg.name = name
            pkg.monthly_rate = _parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            pkg.grace_period_days = _parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            pkg.includes_emergency_service = includes_emergency
            pkg.emergency_monthly_rate = _parse_decimal_field(emergency_rate, label="Emergency add-on rate", min_value=Decimal("0.00"))
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


from .guarding_asset_console import GuardingAssetsView  # noqa: E402
