from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    ClockEvent,
    DispatchTask,
    FieldReport,
    GuardApplicant,
    GuardPanicAlert,
    GuardProfile,
    PatrolRound,
    Shift,
    ShiftAssignment,
    WelfareCheck,
)


def _ensure_transition(current_status: str, next_status: str, allowed: dict[str, set[str]], *, label: str) -> None:
    if not next_status or current_status == next_status:
        return
    if next_status not in allowed.get(current_status, set()):
        raise ValidationError({"status": f"{label} cannot move from {current_status} to {next_status}."})


def ensure_shift_time_order(starts_at, ends_at) -> None:
    if starts_at and ends_at and ends_at <= starts_at:
        raise ValidationError({"ends_at": "Shift end time must be after the start time."})


def ensure_assignment_matches_route(patrol_round: PatrolRound) -> None:
    if patrol_round.assignment and patrol_round.assignment.shift.post_id != patrol_round.route.post_id:
        raise ValidationError({"assignment": "Assignment post must match the patrol route post."})


def ensure_applicant_status_transition(applicant: GuardApplicant, status: str) -> None:
    allowed = {
        GuardApplicant.Status.APPLIED: {
            GuardApplicant.Status.SCREENING,
            GuardApplicant.Status.REJECTED,
            GuardApplicant.Status.WITHDRAWN,
        },
        GuardApplicant.Status.SCREENING: {
            GuardApplicant.Status.INTERVIEW,
            GuardApplicant.Status.BACKGROUND_CHECK,
            GuardApplicant.Status.REJECTED,
            GuardApplicant.Status.WITHDRAWN,
        },
        GuardApplicant.Status.INTERVIEW: {
            GuardApplicant.Status.BACKGROUND_CHECK,
            GuardApplicant.Status.OFFERED,
            GuardApplicant.Status.REJECTED,
            GuardApplicant.Status.WITHDRAWN,
        },
        GuardApplicant.Status.BACKGROUND_CHECK: {
            GuardApplicant.Status.OFFERED,
            GuardApplicant.Status.REJECTED,
            GuardApplicant.Status.WITHDRAWN,
        },
        GuardApplicant.Status.OFFERED: {
            GuardApplicant.Status.REJECTED,
            GuardApplicant.Status.WITHDRAWN,
        },
        GuardApplicant.Status.HIRED: set(),
        GuardApplicant.Status.REJECTED: set(),
        GuardApplicant.Status.WITHDRAWN: set(),
    }
    _ensure_transition(applicant.status, status, allowed, label="Applicant")


def ensure_guard_status_transition(guard: GuardProfile, status: str) -> None:
    allowed = {
        GuardProfile.Status.ACTIVE: {
            GuardProfile.Status.SUSPENDED,
            GuardProfile.Status.INACTIVE,
            GuardProfile.Status.TERMINATED,
        },
        GuardProfile.Status.SUSPENDED: {
            GuardProfile.Status.ACTIVE,
            GuardProfile.Status.INACTIVE,
            GuardProfile.Status.TERMINATED,
        },
        GuardProfile.Status.INACTIVE: {
            GuardProfile.Status.ACTIVE,
            GuardProfile.Status.TERMINATED,
        },
        GuardProfile.Status.TERMINATED: set(),
    }
    _ensure_transition(guard.status, status, allowed, label="Guard")


@transaction.atomic
def hire_applicant(applicant: GuardApplicant, *, employee_number: str, actor=None) -> GuardProfile:
    if applicant.hired_guard_id:
        raise ValidationError({"applicant": "Applicant has already been converted to a guard profile."})
    if not employee_number:
        raise ValidationError({"employee_number": "Employee number is required."})
    if applicant.status != GuardApplicant.Status.OFFERED:
        raise ValidationError({"status": "Only offered applicants can be hired."})

    guard = GuardProfile.objects.create(
        employee_number=employee_number,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        phone_number=applicant.phone_number,
        email=applicant.email,
        home_address=applicant.address,
        hire_date=timezone.localdate(),
        metadata={"applicant_id": str(applicant.id), "hired_by": getattr(actor, "id", None)},
    )
    applicant.status = GuardApplicant.Status.HIRED
    applicant.hired_guard = guard
    applicant.save(update_fields=["status", "hired_guard", "updated_at"])
    return guard


def ensure_shift_status_transition(shift: Shift, status: str) -> None:
    if status not in Shift.Status.values:
        raise ValidationError({"status": "Unsupported shift status."})
    allowed = {
        Shift.Status.DRAFT: {Shift.Status.PUBLISHED, Shift.Status.CANCELLED},
        Shift.Status.PUBLISHED: {Shift.Status.IN_PROGRESS, Shift.Status.CANCELLED},
        Shift.Status.IN_PROGRESS: {Shift.Status.COMPLETED, Shift.Status.CANCELLED},
        Shift.Status.COMPLETED: set(),
        Shift.Status.CANCELLED: set(),
    }
    _ensure_transition(shift.status, status, allowed, label="Shift")
    if status == Shift.Status.IN_PROGRESS and not shift.assignments.exists():
        raise ValidationError({"assignments": "A shift needs at least one assignment before it can start."})


def transition_shift(shift: Shift, status: str) -> Shift:
    ensure_shift_status_transition(shift, status)
    shift.status = status
    shift.save(update_fields=["status", "updated_at"])
    return shift


def ensure_assignment_status_transition(assignment: ShiftAssignment, status: str) -> None:
    if status not in ShiftAssignment.Status.values:
        raise ValidationError({"status": "Unsupported assignment status."})
    allowed = {
        ShiftAssignment.Status.ASSIGNED: {
            ShiftAssignment.Status.ACCEPTED,
            ShiftAssignment.Status.DECLINED,
            ShiftAssignment.Status.NO_SHOW,
            ShiftAssignment.Status.REMOVED,
        },
        ShiftAssignment.Status.ACCEPTED: {
            ShiftAssignment.Status.CLOCKED_IN,
            ShiftAssignment.Status.DECLINED,
            ShiftAssignment.Status.NO_SHOW,
            ShiftAssignment.Status.REMOVED,
        },
        ShiftAssignment.Status.DECLINED: {ShiftAssignment.Status.ACCEPTED, ShiftAssignment.Status.REMOVED},
        ShiftAssignment.Status.CLOCKED_IN: {ShiftAssignment.Status.CLOCKED_OUT},
        ShiftAssignment.Status.CLOCKED_OUT: set(),
        ShiftAssignment.Status.NO_SHOW: set(),
        ShiftAssignment.Status.REMOVED: set(),
    }
    _ensure_transition(assignment.status, status, allowed, label="Assignment")


def transition_assignment(assignment: ShiftAssignment, status: str, *, note: str = "") -> ShiftAssignment:
    ensure_assignment_status_transition(assignment, status)
    assignment.status = status
    if status == ShiftAssignment.Status.ACCEPTED and assignment.accepted_at is None:
        assignment.accepted_at = timezone.now()
    if note:
        assignment.notes = note
    assignment.save(update_fields=["status", "accepted_at", "notes", "updated_at"])
    return assignment


def accept_assignment(assignment: ShiftAssignment) -> ShiftAssignment:
    return transition_assignment(assignment, ShiftAssignment.Status.ACCEPTED)


def decline_assignment(assignment: ShiftAssignment, *, note: str = "") -> ShiftAssignment:
    return transition_assignment(assignment, ShiftAssignment.Status.DECLINED, note=note)


def mark_assignment_no_show(assignment: ShiftAssignment, *, note: str = "") -> ShiftAssignment:
    return transition_assignment(assignment, ShiftAssignment.Status.NO_SHOW, note=note)


def record_clock_event(
    assignment: ShiftAssignment,
    *,
    event_type: str,
    latitude=None,
    longitude=None,
    accuracy_m=None,
    within_geofence=False,
    device_timestamp=None,
) -> ClockEvent:
    if event_type not in ClockEvent.EventType.values:
        raise ValidationError({"event_type": "Unsupported clock event type."})
    if assignment.status in {ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW}:
        raise ValidationError({"assignment": "This assignment is closed."})
    if event_type == ClockEvent.EventType.CLOCK_IN:
        ensure_assignment_status_transition(assignment, ShiftAssignment.Status.CLOCKED_IN)
    elif event_type == ClockEvent.EventType.CLOCK_OUT:
        ensure_assignment_status_transition(assignment, ShiftAssignment.Status.CLOCKED_OUT)
    elif assignment.status != ShiftAssignment.Status.CLOCKED_IN:
        raise ValidationError({"assignment": "Break events require a clocked-in assignment."})

    clock_event = ClockEvent.objects.create(
        assignment=assignment,
        event_type=event_type,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        within_geofence=within_geofence,
        device_timestamp=device_timestamp,
    )
    if event_type == ClockEvent.EventType.CLOCK_IN:
        assignment.status = ShiftAssignment.Status.CLOCKED_IN
        assignment.clocked_in_at = assignment.clocked_in_at or clock_event.created_at
        assignment.save(update_fields=["status", "clocked_in_at", "updated_at"])
    elif event_type == ClockEvent.EventType.CLOCK_OUT:
        assignment.status = ShiftAssignment.Status.CLOCKED_OUT
        assignment.clocked_out_at = clock_event.created_at
        assignment.save(update_fields=["status", "clocked_out_at", "updated_at"])
    return clock_event


def ensure_patrol_round_status_transition(patrol_round: PatrolRound, status: str) -> None:
    if status not in PatrolRound.Status.values:
        raise ValidationError({"status": "Unsupported patrol round status."})
    allowed = {
        PatrolRound.Status.SCHEDULED: {
            PatrolRound.Status.IN_PROGRESS,
            PatrolRound.Status.MISSED,
            PatrolRound.Status.CANCELLED,
        },
        PatrolRound.Status.IN_PROGRESS: {
            PatrolRound.Status.COMPLETED,
            PatrolRound.Status.MISSED,
            PatrolRound.Status.CANCELLED,
        },
        PatrolRound.Status.COMPLETED: set(),
        PatrolRound.Status.MISSED: set(),
        PatrolRound.Status.CANCELLED: set(),
    }
    _ensure_transition(patrol_round.status, status, allowed, label="Patrol round")


def transition_patrol_round(patrol_round: PatrolRound, status: str) -> PatrolRound:
    ensure_patrol_round_status_transition(patrol_round, status)
    if status == PatrolRound.Status.COMPLETED:
        return complete_patrol_round(patrol_round)
    now = timezone.now()
    patrol_round.status = status
    if status == PatrolRound.Status.IN_PROGRESS and patrol_round.started_at is None:
        patrol_round.started_at = now
    patrol_round.save(update_fields=["status", "started_at", "updated_at"])
    return patrol_round


def complete_patrol_round(patrol_round: PatrolRound) -> PatrolRound:
    ensure_patrol_round_status_transition(patrol_round, PatrolRound.Status.COMPLETED)
    expected_checkpoint_ids = set(
        patrol_round.route.patrolroutecheckpoint_set.values_list("checkpoint_id", flat=True)
    )
    scanned_checkpoint_ids = set(patrol_round.scans.values_list("checkpoint_id", flat=True))
    if expected_checkpoint_ids and not expected_checkpoint_ids.issubset(scanned_checkpoint_ids):
        raise ValidationError({"checkpoints": "All route checkpoints must be scanned before completion."})
    now = timezone.now()
    patrol_round.status = PatrolRound.Status.COMPLETED
    patrol_round.completed_at = now
    if patrol_round.started_at is None:
        patrol_round.started_at = now
    patrol_round.save(update_fields=["status", "started_at", "completed_at", "updated_at"])
    return patrol_round


def ensure_report_status_transition(report: FieldReport, status: str) -> None:
    if status not in FieldReport.Status.values:
        raise ValidationError({"status": "Unsupported report status."})
    allowed = {
        FieldReport.Status.DRAFT: {FieldReport.Status.SUBMITTED},
        FieldReport.Status.SUBMITTED: {FieldReport.Status.APPROVED, FieldReport.Status.REJECTED},
        FieldReport.Status.APPROVED: set(),
        FieldReport.Status.REJECTED: set(),
    }
    _ensure_transition(report.status, status, allowed, label="Report")


def transition_field_report(report: FieldReport, status: str) -> FieldReport:
    ensure_report_status_transition(report, status)
    report.status = status
    report.save(update_fields=["status", "updated_at"])
    return report


def review_field_report(report: FieldReport, *, actor, status: str, note: str = "") -> FieldReport:
    if status not in {FieldReport.Status.APPROVED, FieldReport.Status.REJECTED}:
        raise ValidationError({"status": "Reports can only be approved or rejected during review."})
    ensure_report_status_transition(report, status)
    report.status = status
    report.reviewed_by = actor
    report.reviewed_at = timezone.now()
    report.review_note = note
    report.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    return report


def respond_to_welfare_check(check: WelfareCheck, *, note: str = "") -> WelfareCheck:
    if check.status not in {WelfareCheck.Status.PENDING, WelfareCheck.Status.ESCALATED}:
        raise ValidationError({"status": "This welfare check is already closed."})
    check.status = WelfareCheck.Status.CONFIRMED
    check.responded_at = timezone.now()
    check.response_note = note
    check.save(update_fields=["status", "responded_at", "response_note", "updated_at"])
    return check


def ensure_panic_alert_status_transition(alert: GuardPanicAlert, status: str) -> None:
    if status not in GuardPanicAlert.Status.values:
        raise ValidationError({"status": "Unsupported panic alert status."})
    allowed = {
        GuardPanicAlert.Status.OPEN: {
            GuardPanicAlert.Status.ACKNOWLEDGED,
            GuardPanicAlert.Status.RESOLVED,
            GuardPanicAlert.Status.CANCELLED,
        },
        GuardPanicAlert.Status.ACKNOWLEDGED: {
            GuardPanicAlert.Status.RESOLVED,
            GuardPanicAlert.Status.CANCELLED,
        },
        GuardPanicAlert.Status.RESOLVED: set(),
        GuardPanicAlert.Status.CANCELLED: set(),
    }
    _ensure_transition(alert.status, status, allowed, label="Panic alert")


def acknowledge_panic_alert(alert: GuardPanicAlert, *, actor) -> GuardPanicAlert:
    ensure_panic_alert_status_transition(alert, GuardPanicAlert.Status.ACKNOWLEDGED)
    alert.status = GuardPanicAlert.Status.ACKNOWLEDGED
    alert.acknowledged_by = actor
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at", "updated_at"])
    return alert


def resolve_panic_alert(alert: GuardPanicAlert, *, actor) -> GuardPanicAlert:
    ensure_panic_alert_status_transition(alert, GuardPanicAlert.Status.RESOLVED)
    now = timezone.now()
    alert.status = GuardPanicAlert.Status.RESOLVED
    alert.resolved_by = actor
    alert.resolved_at = now
    if alert.acknowledged_at is None:
        alert.acknowledged_by = actor
        alert.acknowledged_at = now
    alert.save(
        update_fields=[
            "status",
            "acknowledged_by",
            "acknowledged_at",
            "resolved_by",
            "resolved_at",
            "updated_at",
        ]
    )
    return alert


def transition_panic_alert(alert: GuardPanicAlert, *, status: str, actor=None) -> GuardPanicAlert:
    if status == GuardPanicAlert.Status.ACKNOWLEDGED:
        return acknowledge_panic_alert(alert, actor=actor)
    if status == GuardPanicAlert.Status.RESOLVED:
        return resolve_panic_alert(alert, actor=actor)
    ensure_panic_alert_status_transition(alert, status)
    alert.status = status
    if status == GuardPanicAlert.Status.CANCELLED:
        alert.resolved_by = actor
        alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])
    return alert


def ensure_dispatch_status_transition(task: DispatchTask, status: str) -> None:
    if status not in DispatchTask.Status.values:
        raise ValidationError({"status": "Unsupported dispatch status."})
    allowed = {
        DispatchTask.Status.OPEN: {DispatchTask.Status.ASSIGNED, DispatchTask.Status.CANCELLED},
        DispatchTask.Status.ASSIGNED: {DispatchTask.Status.ACCEPTED, DispatchTask.Status.CANCELLED},
        DispatchTask.Status.ACCEPTED: {DispatchTask.Status.EN_ROUTE, DispatchTask.Status.CANCELLED},
        DispatchTask.Status.EN_ROUTE: {DispatchTask.Status.ARRIVED, DispatchTask.Status.CANCELLED},
        DispatchTask.Status.ARRIVED: {DispatchTask.Status.RESOLVED, DispatchTask.Status.CANCELLED},
        DispatchTask.Status.RESOLVED: set(),
        DispatchTask.Status.CANCELLED: set(),
    }
    _ensure_transition(task.status, status, allowed, label="Dispatch task")


def transition_dispatch_task(task: DispatchTask, *, status: str, actor=None, note: str = "") -> DispatchTask:
    ensure_dispatch_status_transition(task, status)
    if status in {DispatchTask.Status.ASSIGNED, DispatchTask.Status.ACCEPTED, DispatchTask.Status.EN_ROUTE}:
        if task.assigned_guard_id is None:
            raise ValidationError({"assigned_guard": "A guard must be assigned before this transition."})

    now = timezone.now()
    task.status = status
    if status == DispatchTask.Status.ASSIGNED:
        task.assigned_at = task.assigned_at or now
    elif status == DispatchTask.Status.ACCEPTED:
        task.accepted_at = task.accepted_at or now
    elif status == DispatchTask.Status.EN_ROUTE:
        task.en_route_at = task.en_route_at or now
    elif status == DispatchTask.Status.ARRIVED:
        task.arrived_at = task.arrived_at or now
    elif status == DispatchTask.Status.RESOLVED:
        task.resolved_at = task.resolved_at or now
        task.resolution_note = note
    elif status == DispatchTask.Status.CANCELLED:
        task.cancelled_at = task.cancelled_at or now
        task.resolution_note = note

    task.save(
        update_fields=[
            "status",
            "assigned_at",
            "accepted_at",
            "en_route_at",
            "arrived_at",
            "resolved_at",
            "cancelled_at",
            "resolution_note",
            "updated_at",
        ]
    )
    return task
