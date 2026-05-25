from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.communication.models import BroadcastMessage
from apps.communication.tasks import send_broadcast_push_notifications

from .models import (
    DispatchTask,
    GuardCredential,
    GuardDocument,
    GuardTimesheet,
    GuardTrainingRecord,
    GuardingEventLog,
    PatrolRound,
    ShiftAssignment,
    WelfareCheck,
)
from .services import build_timesheet_for_assignment, mark_assignment_no_show, transition_patrol_round


WELFARE_WARNING_MINUTES = 10
LATE_CLOCK_IN_MINUTES = 10
NO_SHOW_MINUTES = 30
EXPIRY_WARNING_DAYS = 30
DISPATCH_ASSIGNMENT_SLA_MINUTES = 5
DISPATCH_ACCEPTED_SLA_MINUTES = 10
DISPATCH_EN_ROUTE_SLA_MINUTES = 30
DISPATCH_ARRIVED_SLA_MINUTES = 15


def _object_identity(obj):
    return obj._meta.label_lower, str(obj.pk)


def _create_event(
    *,
    event_type,
    title,
    message="",
    severity=GuardingEventLog.Severity.INFO,
    source=GuardingEventLog.Source.SYSTEM,
    obj=None,
    guard=None,
    site=None,
    actor=None,
    metadata=None,
    unique_key=None,
):
    object_label = ""
    object_id = ""
    if obj is not None:
        object_label, object_id = _object_identity(obj)
    data = {
        "event_type": event_type,
        "severity": severity,
        "source": source,
        "title": title,
        "message": message,
        "object_label": object_label,
        "object_id": object_id,
        "guard": guard,
        "site": site,
        "actor": actor,
        "metadata": metadata or {},
    }
    if not unique_key:
        return GuardingEventLog.objects.create(**data)
    event, created = GuardingEventLog.objects.get_or_create(unique_key=unique_key, defaults=data)
    return event if created else None


def _notify_guard(guard, *, title, body, event=None, push_data=None):
    user = getattr(guard, "user", None)
    if user is None:
        return None
    payload = dict(push_data or {})
    if event is not None:
        payload.setdefault("event_type", event.event_type)
        payload.setdefault("object_id", event.object_id)
        payload.setdefault("severity", event.severity)
        route = "guard/home"
        if event.event_type.startswith("dispatch_"):
            route = "guard/dispatch"
        elif event.event_type.startswith("welfare_"):
            route = "guard/welfare"
        elif event.event_type.startswith("patrol_"):
            route = "guard/patrol"
        elif event.event_type.startswith("panic"):
            route = "guard/panic"
        payload.setdefault("route", route)
    message = BroadcastMessage.objects.create(
        title=title,
        body=body,
        message_type=BroadcastMessage.TYPE_ALERT,
        send_push=True,
        send_email=False,
        send_sms=False,
        recipient=user,
        status=BroadcastMessage.STATUS_PENDING,
        push_data=payload,
    )
    if event is not None:
        event.metadata = {**event.metadata, "broadcast_message_id": str(message.id)}
        event.save(update_fields=["metadata"])
    send_broadcast_push_notifications.delay(str(message.id))
    return message


def _guard_for_welfare_check(check):
    return check.assignment.guard if check.assignment_id else None


def _site_for_welfare_check(check):
    return check.assignment.shift.post.site if check.assignment_id else None


def _guard_for_patrol_round(patrol_round):
    return patrol_round.assignment.guard if patrol_round.assignment_id else None


def _site_for_patrol_round(patrol_round):
    return patrol_round.route.post.site if patrol_round.route_id else None


@shared_task
def warn_due_welfare_checks():
    now = timezone.now()
    cutoff = now + timedelta(minutes=WELFARE_WARNING_MINUTES)
    checks = (
        WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post__site")
        .filter(status=WelfareCheck.Status.PENDING, due_at__gt=now, due_at__lte=cutoff)
        .order_by("due_at")[:100]
    )
    created_count = 0
    for check in checks:
        guard = _guard_for_welfare_check(check)
        site = _site_for_welfare_check(check)
        event = _create_event(
            event_type="welfare_due_soon",
            severity=GuardingEventLog.Severity.WARNING,
            title="Welfare check due soon",
            message=f"Welfare check for {guard or 'guard'} is due at {check.due_at:%Y-%m-%d %H:%M}.",
            obj=check,
            guard=guard,
            site=site,
            unique_key=f"welfare_due_soon:{check.pk}",
            metadata={"due_at": check.due_at.isoformat()},
        )
        if event:
            created_count += 1
            _notify_guard(
                guard,
                title="Welfare check due soon",
                body=f"Please confirm your welfare check by {check.due_at:%H:%M}.",
                event=event,
            )
    return created_count


@shared_task
def mark_overdue_welfare_checks():
    now = timezone.now()
    checks = (
        WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post__site")
        .filter(status=WelfareCheck.Status.PENDING, due_at__lt=now)
        .order_by("due_at")[:200]
    )
    updated = 0
    for check in checks:
        with transaction.atomic():
            check.status = WelfareCheck.Status.MISSED
            check.save(update_fields=["status", "updated_at"])
            guard = _guard_for_welfare_check(check)
            site = _site_for_welfare_check(check)
            event = _create_event(
                event_type="welfare_missed",
                severity=GuardingEventLog.Severity.CRITICAL,
                title="Welfare check missed",
                message=f"Welfare check for {guard or 'guard'} was missed.",
                obj=check,
                guard=guard,
                site=site,
                unique_key=f"welfare_missed:{check.pk}",
                metadata={"due_at": check.due_at.isoformat()},
            )
            if event:
                _notify_guard(
                    guard,
                    title="Welfare check missed",
                    body="Your welfare check is overdue. Contact control immediately.",
                    event=event,
                )
            updated += 1
    return updated


@shared_task
def mark_overdue_patrol_rounds():
    now = timezone.now()
    rounds = (
        PatrolRound.objects.select_related("route", "route__post__site", "assignment", "assignment__guard")
        .filter(
            status__in=[PatrolRound.Status.SCHEDULED, PatrolRound.Status.IN_PROGRESS],
            scheduled_end__lt=now,
        )
        .order_by("scheduled_end")[:200]
    )
    updated = 0
    for patrol_round in rounds:
        try:
            transition_patrol_round(patrol_round, PatrolRound.Status.MISSED)
        except Exception:
            patrol_round.status = PatrolRound.Status.MISSED
            patrol_round.save(update_fields=["status", "updated_at"])
        guard = _guard_for_patrol_round(patrol_round)
        site = _site_for_patrol_round(patrol_round)
        event = _create_event(
            event_type="patrol_round_missed",
            severity=GuardingEventLog.Severity.CRITICAL,
            title="Patrol round missed",
            message=f"{patrol_round.route.name} ended without completion.",
            obj=patrol_round,
            guard=guard,
            site=site,
            unique_key=f"patrol_round_missed:{patrol_round.pk}",
            metadata={"scheduled_end": patrol_round.scheduled_end.isoformat() if patrol_round.scheduled_end else ""},
        )
        if event:
            _notify_guard(
                guard,
                title="Patrol round missed",
                body=f"{patrol_round.route.name} is overdue. Contact control.",
                event=event,
            )
        updated += 1
    return updated


@shared_task
def escalate_dispatch_sla_breaches():
    now = timezone.now()
    tasks = (
        DispatchTask.objects.select_related("site", "assigned_guard", "assigned_guard__user")
        .exclude(status__in=[DispatchTask.Status.RESOLVED, DispatchTask.Status.CANCELLED])
        .order_by("created_at")[:300]
    )
    created_count = 0
    for task in tasks:
        checks = []
        if task.status == DispatchTask.Status.OPEN:
            checks.append(("dispatch_unassigned_sla", task.created_at, DISPATCH_ASSIGNMENT_SLA_MINUTES, "Dispatch still unassigned", GuardingEventLog.Severity.CRITICAL))
        elif task.status == DispatchTask.Status.ASSIGNED:
            checks.append(("dispatch_accept_sla", task.assigned_at or task.created_at, DISPATCH_ASSIGNMENT_SLA_MINUTES, "Dispatch not accepted", GuardingEventLog.Severity.WARNING))
        elif task.status == DispatchTask.Status.ACCEPTED:
            checks.append(("dispatch_en_route_sla", task.accepted_at or task.updated_at, DISPATCH_ACCEPTED_SLA_MINUTES, "Dispatch not en-route", GuardingEventLog.Severity.WARNING))
        elif task.status == DispatchTask.Status.EN_ROUTE:
            checks.append(("dispatch_arrival_sla", task.en_route_at or task.updated_at, DISPATCH_EN_ROUTE_SLA_MINUTES, "Dispatch arrival overdue", GuardingEventLog.Severity.WARNING))
        elif task.status == DispatchTask.Status.ARRIVED:
            checks.append(("dispatch_resolution_sla", task.arrived_at or task.updated_at, DISPATCH_ARRIVED_SLA_MINUTES, "Dispatch resolution overdue", GuardingEventLog.Severity.WARNING))

        for event_type, started_at, minutes, title, severity in checks:
            if started_at and now - started_at < timedelta(minutes=minutes):
                continue
            event = _create_event(
                event_type=event_type,
                severity=severity,
                title=title,
                message=f"{task.title} has been {task.get_status_display().lower()} for more than {minutes} minutes.",
                obj=task,
                guard=task.assigned_guard,
                site=task.site,
                unique_key=f"{event_type}:{task.pk}",
                metadata={"status": task.status, "sla_minutes": minutes},
            )
            if event:
                created_count += 1
                _notify_guard(
                    task.assigned_guard,
                    title=title,
                    body=f"{task.title}: please update your dispatch status.",
                    event=event,
                )
    return created_count


@shared_task
def warn_expiring_guard_records():
    today = timezone.localdate()
    cutoff = today + timedelta(days=EXPIRY_WARNING_DAYS)
    created_count = 0

    credentials = (
        GuardCredential.objects.select_related("guard", "guard__user")
        .filter(expires_on__isnull=False, expires_on__gte=today, expires_on__lte=cutoff)
        .order_by("expires_on")[:200]
    )
    for credential in credentials:
        event = _create_event(
            event_type="credential_expiring",
            severity=GuardingEventLog.Severity.WARNING,
            title="Credential expiring",
            message=f"{credential.name} for {credential.guard.full_name} expires on {credential.expires_on:%Y-%m-%d}.",
            obj=credential,
            guard=credential.guard,
            unique_key=f"credential_expiring:{credential.pk}:{credential.expires_on}",
            metadata={"expires_on": credential.expires_on.isoformat()},
        )
        if event:
            created_count += 1
            _notify_guard(
                credential.guard,
                title="Credential expiring",
                body=f"{credential.name} expires on {credential.expires_on:%Y-%m-%d}.",
                event=event,
            )

    documents = (
        GuardDocument.objects.select_related("guard", "guard__user")
        .filter(expires_on__isnull=False, expires_on__gte=today, expires_on__lte=cutoff)
        .order_by("expires_on")[:200]
    )
    for document in documents:
        event = _create_event(
            event_type="document_expiring",
            severity=GuardingEventLog.Severity.WARNING,
            title="Document expiring",
            message=f"{document.title} for {document.guard.full_name} expires on {document.expires_on:%Y-%m-%d}.",
            obj=document,
            guard=document.guard,
            unique_key=f"document_expiring:{document.pk}:{document.expires_on}",
            metadata={"expires_on": document.expires_on.isoformat()},
        )
        if event:
            created_count += 1
            _notify_guard(
                document.guard,
                title="Document expiring",
                body=f"{document.title} expires on {document.expires_on:%Y-%m-%d}.",
                event=event,
            )

    training_records = (
        GuardTrainingRecord.objects.select_related("guard", "guard__user")
        .filter(expires_on__isnull=False, expires_on__gte=today, expires_on__lte=cutoff)
        .order_by("expires_on")[:200]
    )
    for record in training_records:
        event = _create_event(
            event_type="training_expiring",
            severity=GuardingEventLog.Severity.WARNING,
            title="Training expiring",
            message=f"{record.name} for {record.guard.full_name} expires on {record.expires_on:%Y-%m-%d}.",
            obj=record,
            guard=record.guard,
            unique_key=f"training_expiring:{record.pk}:{record.expires_on}",
            metadata={"expires_on": record.expires_on.isoformat()},
        )
        if event:
            created_count += 1
            _notify_guard(
                record.guard,
                title="Training expiring",
                body=f"{record.name} expires on {record.expires_on:%Y-%m-%d}.",
                event=event,
            )
    return created_count


@shared_task
def flag_late_and_no_show_assignments():
    now = timezone.now()
    late_cutoff = now - timedelta(minutes=LATE_CLOCK_IN_MINUTES)
    no_show_cutoff = now - timedelta(minutes=NO_SHOW_MINUTES)
    assignments = (
        ShiftAssignment.objects.select_related("guard", "guard__user", "shift", "shift__post", "shift__post__site")
        .filter(
            status__in=[ShiftAssignment.Status.ASSIGNED, ShiftAssignment.Status.ACCEPTED],
            shift__starts_at__lt=late_cutoff,
            clocked_in_at__isnull=True,
        )
        .order_by("shift__starts_at")[:300]
    )
    created_count = 0
    for assignment in assignments:
        if assignment.shift.starts_at < no_show_cutoff:
            if assignment.status != ShiftAssignment.Status.NO_SHOW:
                mark_assignment_no_show(assignment, note="Automatically marked no-show after missed clock-in.")
            event_type = "assignment_no_show"
            title = "No-show detected"
            severity = GuardingEventLog.Severity.CRITICAL
            unique_key = f"assignment_no_show:{assignment.pk}"
        else:
            event_type = "assignment_late_clock_in"
            title = "Late clock-in"
            severity = GuardingEventLog.Severity.WARNING
            unique_key = f"assignment_late_clock_in:{assignment.pk}"
        event = _create_event(
            event_type=event_type,
            severity=severity,
            title=title,
            message=f"{assignment.guard.full_name} has not clocked in for {assignment.shift.post.name}.",
            obj=assignment,
            guard=assignment.guard,
            site=assignment.shift.post.site,
            unique_key=unique_key,
            metadata={"shift_start": assignment.shift.starts_at.isoformat()},
        )
        if event:
            created_count += 1
            _notify_guard(
                assignment.guard,
                title=title,
                body=f"Shift at {assignment.shift.post.name} started at {assignment.shift.starts_at:%H:%M}.",
                event=event,
            )
    return created_count


@shared_task
def generate_ready_timesheets():
    assignments = (
        ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
        .filter(
            status=ShiftAssignment.Status.CLOCKED_OUT,
            clocked_in_at__isnull=False,
            clocked_out_at__isnull=False,
            timesheet__isnull=True,
        )
        .order_by("clocked_out_at")[:300]
    )
    created_count = 0
    for assignment in assignments:
        timesheet = build_timesheet_for_assignment(assignment)
        if timesheet:
            created_count += 1
    return created_count


@shared_task
def purge_old_guard_location_pings():
    from .services import purge_old_location_pings

    return purge_old_location_pings()


@shared_task
def flag_overdue_asset_returns():
    from datetime import timedelta

    from .asset_models import ShiftAssetManifest

    cutoff = timezone.now() - timedelta(hours=24)
    manifests = ShiftAssetManifest.objects.select_related(
        "assignment__guard",
        "assignment__shift__post",
        "assignment__shift__post__site",
    ).filter(
        status__in=[
            ShiftAssetManifest.Status.ISSUED,
            ShiftAssetManifest.Status.PARTIAL_RETURN,
        ],
        assignment__clocked_out_at__isnull=False,
        assignment__clocked_out_at__lt=cutoff,
    )[:200]
    created_count = 0
    for manifest in manifests:
        unique_key = f"asset_overdue_return:{manifest.pk}"
        event = _create_event(
            event_type="asset_return_overdue",
            severity=GuardingEventLog.Severity.WARNING,
            title="Asset return overdue",
            message=(
                f"{manifest.assignment.guard.full_name} clocked out but assets "
                f"for {manifest.assignment.shift.post.name} are not fully returned."
            ),
            obj=manifest,
            guard=manifest.assignment.guard,
            site=manifest.assignment.shift.post.site,
            unique_key=unique_key,
        )
        if event:
            created_count += 1
    return created_count


@shared_task
def run_guarding_automation():
    return {
        "welfare_due_soon": warn_due_welfare_checks(),
        "welfare_missed": mark_overdue_welfare_checks(),
        "patrol_rounds_missed": mark_overdue_patrol_rounds(),
        "dispatch_sla": escalate_dispatch_sla_breaches(),
        "expiring_records": warn_expiring_guard_records(),
        "late_no_show_assignments": flag_late_and_no_show_assignments(),
        "timesheets_generated": generate_ready_timesheets(),
        "asset_returns_overdue": flag_overdue_asset_returns(),
    }
