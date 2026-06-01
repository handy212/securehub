from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    ClientPortalAccess,
    DispatchTask,
    FieldReport,
    FieldReportAcknowledgement,
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantProfile,
    GuardAvailability,
    GuardContract,
    GuardCredential,
    GuardDocument,
    GuardInvoice,
    GuardInvoiceLine,
    GuardTimesheet,
    GuardTrainingRecord,
    GuardingEventLog,
    GuardingPrivacySettings,
    GuardLocationPing,
    LeaveRequest,
    GuardPanicAlert,
    GuardProfile,
    PatrolRound,
    PostOrder,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    WelfareCheck,
)


def _ensure_transition(current_status: str, next_status: str, allowed: dict[str, set[str]], *, label: str) -> None:
    if not next_status or current_status == next_status:
        return
    if next_status not in allowed.get(current_status, set()):
        raise ValidationError({"status": f"{label} cannot move from {current_status} to {next_status}."})


def create_workflow_event(
    *,
    event_type: str,
    title: str,
    message: str = "",
    severity: str = GuardingEventLog.Severity.INFO,
    source: str = GuardingEventLog.Source.API,
    obj=None,
    guard=None,
    site=None,
    actor=None,
    metadata=None,
    unique_key: str = "",
) -> GuardingEventLog | None:
    object_label = ""
    object_id = ""
    if obj is not None:
        object_label = obj._meta.label_lower
        object_id = str(obj.pk)
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
    if unique_key:
        event, created = GuardingEventLog.objects.get_or_create(unique_key=unique_key, defaults=data)
        return event if created else None
    return GuardingEventLog.objects.create(**data)


def ensure_shift_time_order(starts_at, ends_at) -> None:
    if starts_at and ends_at and ends_at <= starts_at:
        raise ValidationError({"ends_at": "Shift end time must be after the start time."})


def ensure_guard_available_for_shift(guard: GuardProfile, shift: Shift, *, assignment: ShiftAssignment | None = None) -> None:
    overlapping_assignments = ShiftAssignment.objects.filter(
        guard=guard,
        shift__starts_at__lt=shift.ends_at,
        shift__ends_at__gt=shift.starts_at,
    ).exclude(status__in=[ShiftAssignment.Status.DECLINED, ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW])
    if assignment and assignment.pk:
        overlapping_assignments = overlapping_assignments.exclude(pk=assignment.pk)
    if overlapping_assignments.exists():
        raise ValidationError({"guard": "Guard already has an overlapping active shift assignment."})

    leave_exists = LeaveRequest.objects.filter(
        guard=guard,
        status=LeaveRequest.Status.APPROVED,
        starts_at__lt=shift.ends_at,
        ends_at__gt=shift.starts_at,
    ).exists()
    if leave_exists:
        raise ValidationError({"guard": "Guard has approved leave during this shift."})

    unavailable_exists = GuardAvailability.objects.filter(
        guard=guard,
        availability_type=GuardAvailability.AvailabilityType.UNAVAILABLE,
        starts_at__lt=shift.ends_at,
        ends_at__gt=shift.starts_at,
    ).exists()
    if unavailable_exists:
        raise ValidationError({"guard": "Guard is marked unavailable during this shift."})


def guard_qualification_gaps(guard: GuardProfile, post) -> list[str]:
    required = [str(item).strip() for item in (post.required_credentials or []) if str(item).strip()]
    if not required:
        return []
    today = timezone.localdate()
    credential_names = set(
        guard.credentials.filter(
            verified=True,
        )
        .filter(models.Q(expires_on__isnull=True) | models.Q(expires_on__gte=today))
        .values_list("name", flat=True)
    )
    training_names = set(
        guard.training_records.filter(
            status="completed",
        )
        .filter(models.Q(expires_on__isnull=True) | models.Q(expires_on__gte=today))
        .values_list("name", flat=True)
    )
    normalized_owned = {name.strip().lower() for name in credential_names | training_names}
    return [item for item in required if item.lower() not in normalized_owned]


def ensure_guard_qualified_for_post(guard: GuardProfile, post) -> None:
    gaps = guard_qualification_gaps(guard, post)
    if gaps:
        raise ValidationError({"guard": f"Guard is missing required qualifications: {', '.join(gaps)}."})


def guard_has_valid_verified_credential(guard: GuardProfile) -> bool:
    today = timezone.localdate()
    return guard.credentials.filter(verified=True).filter(
        models.Q(expires_on__isnull=True) | models.Q(expires_on__gte=today)
    ).exists()


def guard_compliance_issues(guard: GuardProfile) -> list[str]:
    issues: list[str] = []
    if not guard.emergency_contact_name.strip():
        issues.append("Emergency contact name is required.")
    if not guard.emergency_contact_phone.strip():
        issues.append("Emergency contact phone is required.")
    if not guard_has_valid_verified_credential(guard):
        issues.append("At least one verified, non-expired credential is required.")
    return issues


def ensure_guard_compliance_ready(guard: GuardProfile) -> None:
    issues = guard_compliance_issues(guard)
    if issues:
        raise ValidationError({"guard": " ".join(issues)})


def apply_credential_verification(credential: GuardCredential, *, verified: bool, actor=None) -> None:
    credential.verified = verified
    if verified:
        credential.verified_by = actor
        credential.verified_at = timezone.now()
    else:
        credential.verified_by = None
        credential.verified_at = None


def count_non_compliant_active_guards() -> int:
    active_guards = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE)
    return sum(1 for guard in active_guards if guard_compliance_issues(guard))


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
    if status == GuardProfile.Status.ACTIVE and guard.status != GuardProfile.Status.ACTIVE:
        ensure_guard_compliance_ready(guard)


@transaction.atomic
def hire_applicant(applicant: GuardApplicant, *, employee_number: str, actor=None) -> GuardProfile:
    if applicant.hired_guard_id:
        raise ValidationError({"applicant": "Applicant has already been converted to a guard profile."})
    if not employee_number:
        raise ValidationError({"employee_number": "Employee number is required."})
    if applicant.status != GuardApplicant.Status.OFFERED:
        raise ValidationError({"status": "Only offered applicants can be hired."})

    metadata = {
        "applicant_id": str(applicant.id),
        "hired_by": getattr(actor, "id", None),
    }
    if applicant.city:
        metadata["city"] = applicant.city
    if applicant.country:
        metadata["country"] = applicant.country
    if applicant.national_id:
        metadata["national_id"] = applicant.national_id
    if applicant.gps_address:
        metadata["gps_address"] = applicant.gps_address
    if applicant.assigned_branch:
        metadata["assigned_branch"] = applicant.assigned_branch
    if applicant.uniform_size:
        metadata["uniform_size"] = applicant.uniform_size
    if applicant.salary_expectation is not None:
        metadata["salary_expectation"] = str(applicant.salary_expectation)
    if applicant.interview_score is not None:
        metadata["interview_score"] = str(applicant.interview_score)

    guard = GuardProfile.objects.create(
        employee_number=employee_number,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        phone_number=applicant.phone_number or applicant.alternate_phone,
        email=applicant.email,
        home_address=applicant.address or applicant.gps_address,
        emergency_contact_name=applicant.emergency_contact_name,
        emergency_contact_phone=applicant.emergency_contact_phone,
        hire_date=timezone.localdate(),
        status=GuardProfile.Status.INACTIVE,
        metadata=metadata,
        notes=applicant.interview_notes,
    )
    _copy_applicant_documents_to_guard(applicant, guard, actor=actor)
    _copy_applicant_training_from_profile(applicant, guard)
    applicant.status = GuardApplicant.Status.HIRED
    applicant.hired_guard = guard
    applicant.save(update_fields=["status", "hired_guard", "updated_at"])
    create_workflow_event(
        event_type="applicant_hired",
        title="Applicant hired",
        message=f"{applicant.full_name} was converted into guard {guard.employee_number}.",
        obj=applicant,
        guard=guard,
        actor=actor,
        metadata={"employee_number": employee_number},
    )
    return guard


def _map_applicant_document_type(document_type: str) -> str:
    mapping = {
        GuardApplicantDocument.DocumentType.NATIONAL_ID: GuardDocument.DocumentType.ID,
        GuardApplicantDocument.DocumentType.CERTIFICATE: GuardDocument.DocumentType.CERTIFICATE,
        GuardApplicantDocument.DocumentType.REFERENCE_LETTER: GuardDocument.DocumentType.REFERENCE,
        GuardApplicantDocument.DocumentType.POLICE_CLEARANCE: GuardDocument.DocumentType.PERMIT,
        GuardApplicantDocument.DocumentType.CV: GuardDocument.DocumentType.OTHER,
        GuardApplicantDocument.DocumentType.PHOTO: GuardDocument.DocumentType.OTHER,
    }
    return mapping.get(document_type, GuardDocument.DocumentType.OTHER)


def _copy_applicant_documents_to_guard(applicant: GuardApplicant, guard: GuardProfile, *, actor=None) -> None:
    for document in applicant.documents.all():
        GuardDocument.objects.create(
            guard=guard,
            document_type=_map_applicant_document_type(document.document_type),
            title=document.title,
            file=document.file,
            reference_number=document.reference_number,
            notes=document.notes,
            uploaded_by=actor,
        )


def _copy_applicant_training_from_profile(applicant: GuardApplicant, guard: GuardProfile) -> None:
    profile = GuardApplicantProfile.objects.filter(applicant=applicant).first()
    if not profile:
        return
    training_items = []
    if profile.security_training_completed:
        training_items.append("Security Training")
    if profile.fire_safety_training:
        training_items.append("Fire Safety Training")
    if profile.first_aid_certification:
        training_items.append("First Aid Certification")
    for name in training_items:
        GuardTrainingRecord.objects.get_or_create(
            guard=guard,
            name=name,
            defaults={
                "status": GuardTrainingRecord.Status.COMPLETED,
                "completed_on": timezone.localdate(),
            },
        )


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
    previous_status = shift.status
    ensure_shift_status_transition(shift, status)
    shift.status = status
    shift.save(update_fields=["status", "updated_at"])
    create_workflow_event(
        event_type="shift_status_changed",
        title="Shift status changed",
        message=f"Shift moved from {previous_status} to {status}.",
        obj=shift,
        site=shift.post.site,
        metadata={"from": previous_status, "to": status},
    )
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
    previous_status = assignment.status
    ensure_assignment_status_transition(assignment, status)
    assignment.status = status
    if status == ShiftAssignment.Status.ACCEPTED and assignment.accepted_at is None:
        assignment.accepted_at = timezone.now()
    if note:
        assignment.notes = note
    assignment.save(update_fields=["status", "accepted_at", "notes", "updated_at"])
    create_workflow_event(
        event_type="assignment_status_changed",
        title="Assignment status changed",
        message=f"{assignment.guard.full_name} moved from {previous_status} to {status}.",
        obj=assignment,
        guard=assignment.guard,
        site=assignment.shift.post.site,
        metadata={"from": previous_status, "to": status},
    )
    return assignment


@transaction.atomic
def create_shift_swap_request(
    assignment: ShiftAssignment,
    *,
    requested_by: GuardProfile,
    target_guard: GuardProfile | None = None,
    reason: str = "",
) -> ShiftSwapRequest:
    if assignment.guard_id != requested_by.id:
        raise ValidationError({"assignment": "Only the assigned guard can request a swap."})
    if assignment.status not in {ShiftAssignment.Status.ASSIGNED, ShiftAssignment.Status.ACCEPTED}:
        raise ValidationError({"assignment": "Only assigned or accepted shifts can be swapped."})
    if target_guard:
        if target_guard.status != GuardProfile.Status.ACTIVE:
            raise ValidationError({"target_guard": "Target guard must be active."})
        ensure_guard_available_for_shift(target_guard, assignment.shift)
        ensure_guard_qualified_for_post(target_guard, assignment.shift.post)
    swap = ShiftSwapRequest.objects.create(
        assignment=assignment,
        requested_by=requested_by,
        target_guard=target_guard,
        reason=reason,
    )
    create_workflow_event(
        event_type="shift_swap_requested",
        title="Shift swap requested",
        message=f"{requested_by.full_name} requested a shift swap.",
        obj=swap,
        guard=requested_by,
        site=assignment.shift.post.site,
        metadata={"target_guard_id": str(target_guard.id) if target_guard else ""},
    )
    return swap


@transaction.atomic
def review_shift_swap_request(swap: ShiftSwapRequest, *, actor, status: str, note: str = "") -> ShiftSwapRequest:
    if swap.status != ShiftSwapRequest.Status.PENDING:
        raise ValidationError({"status": "Only pending swap requests can be reviewed."})
    if status not in {ShiftSwapRequest.Status.APPROVED, ShiftSwapRequest.Status.REJECTED, ShiftSwapRequest.Status.CANCELLED}:
        raise ValidationError({"status": "Unsupported swap review status."})
    if status == ShiftSwapRequest.Status.APPROVED:
        if swap.target_guard_id is None:
            raise ValidationError({"target_guard": "A target guard is required before approving a swap."})
        ensure_guard_available_for_shift(swap.target_guard, swap.assignment.shift, assignment=swap.assignment)
        ensure_guard_qualified_for_post(swap.target_guard, swap.assignment.shift.post)
        swap.assignment.guard = swap.target_guard
        swap.assignment.status = ShiftAssignment.Status.ASSIGNED
        swap.assignment.accepted_at = None
        swap.assignment.notes = f"Transferred from {swap.requested_by.full_name} by shift swap."
        swap.assignment.save(update_fields=["guard", "status", "accepted_at", "notes", "updated_at"])
    swap.status = status
    swap.review_note = note
    swap.reviewed_by = actor
    swap.reviewed_at = timezone.now()
    swap.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
    create_workflow_event(
        event_type="shift_swap_reviewed",
        title="Shift swap reviewed",
        message=f"Shift swap was {status}.",
        obj=swap,
        guard=swap.target_guard if status == ShiftSwapRequest.Status.APPROVED else swap.requested_by,
        site=swap.assignment.shift.post.site,
        actor=actor,
        metadata={"status": status},
    )
    return swap


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
    skip_asset_check: bool = False,
) -> ClockEvent:
    if event_type not in ClockEvent.EventType.values:
        raise ValidationError({"event_type": "Unsupported clock event type."})
    if assignment.status in {ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW}:
        raise ValidationError({"assignment": "This assignment is closed."})
    if not skip_asset_check:
        from .asset_services import asset_readiness_for_assignment

        phase = "clock_in" if event_type == ClockEvent.EventType.CLOCK_IN else "clock_out"
        if event_type in {ClockEvent.EventType.CLOCK_IN, ClockEvent.EventType.CLOCK_OUT}:
            readiness = asset_readiness_for_assignment(assignment, phase=phase)
            from .asset_models import GuardingAssetPolicy

            if not readiness.ok and readiness.mode == GuardingAssetPolicy.EnforcementMode.STRICT:
                raise ValidationError({"assets": readiness.blockers})
            for warning in readiness.advisory_warnings:
                create_workflow_event(
                    event_type=f"asset_advisory_{phase}",
                    title="Asset advisory",
                    message=warning,
                    guard=assignment.guard,
                    site=assignment.shift.post.site,
                    severity=GuardingEventLog.Severity.WARNING,
                    metadata={"phase": phase, "warnings": readiness.advisory_warnings},
                )
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
    if latitude is not None and longitude is not None:
        GuardLocationPing.objects.create(
            guard=assignment.guard,
            assignment=assignment,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
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
    create_workflow_event(
        event_type=f"clock_{event_type}",
        title=clock_event.get_event_type_display(),
        message=f"{assignment.guard.full_name} recorded {clock_event.get_event_type_display().lower()}.",
        obj=clock_event,
        guard=assignment.guard,
        site=assignment.shift.post.site,
        metadata={"within_geofence": within_geofence},
    )
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
    previous_status = patrol_round.status
    ensure_patrol_round_status_transition(patrol_round, status)
    if status == PatrolRound.Status.COMPLETED:
        return complete_patrol_round(patrol_round)
    now = timezone.now()
    patrol_round.status = status
    if status == PatrolRound.Status.IN_PROGRESS and patrol_round.started_at is None:
        patrol_round.started_at = now
    patrol_round.save(update_fields=["status", "started_at", "updated_at"])
    create_workflow_event(
        event_type="patrol_status_changed",
        title="Patrol status changed",
        message=f"{patrol_round.route.name} moved from {previous_status} to {status}.",
        obj=patrol_round,
        guard=patrol_round.assignment.guard if patrol_round.assignment_id else None,
        site=patrol_round.route.post.site,
        metadata={"from": previous_status, "to": status},
    )
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
    create_workflow_event(
        event_type="patrol_completed",
        title="Patrol completed",
        message=f"{patrol_round.route.name} was completed.",
        obj=patrol_round,
        guard=patrol_round.assignment.guard if patrol_round.assignment_id else None,
        site=patrol_round.route.post.site,
        metadata={"completed_at": now.isoformat()},
    )
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
    create_workflow_event(
        event_type="report_reviewed",
        title="Report reviewed",
        message=f"{report.title} was {status}.",
        obj=report,
        guard=report.guard,
        site=report.site,
        actor=actor,
        metadata={"status": status},
    )
    return report


def respond_to_welfare_check(check: WelfareCheck, *, note: str = "") -> WelfareCheck:
    if check.status not in {WelfareCheck.Status.PENDING, WelfareCheck.Status.MISSED, WelfareCheck.Status.ESCALATED}:
        raise ValidationError({"status": "This welfare check is already closed."})
    check.status = WelfareCheck.Status.CONFIRMED
    check.responded_at = timezone.now()
    check.response_note = note
    check.save(update_fields=["status", "responded_at", "response_note", "updated_at"])
    create_workflow_event(
        event_type="welfare_confirmed",
        title="Welfare check confirmed",
        message=f"Welfare check confirmed by {check.assignment.guard.full_name}.",
        obj=check,
        guard=check.assignment.guard,
        site=check.assignment.shift.post.site,
        metadata={"responded_at": check.responded_at.isoformat()},
    )
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
    create_workflow_event(
        event_type="panic_acknowledged",
        title="Panic alert acknowledged",
        message=f"Panic alert for {alert.guard.full_name} was acknowledged.",
        severity=GuardingEventLog.Severity.WARNING,
        obj=alert,
        guard=alert.guard,
        site=alert.site,
        actor=actor,
    )
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
    create_workflow_event(
        event_type="panic_resolved",
        title="Panic alert resolved",
        message=f"Panic alert for {alert.guard.full_name} was resolved.",
        obj=alert,
        guard=alert.guard,
        site=alert.site,
        actor=actor,
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
    previous_status = task.status
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
    create_workflow_event(
        event_type="dispatch_status_changed",
        title="Dispatch status changed",
        message=f"{task.title} moved from {previous_status} to {status}.",
        obj=task,
        guard=task.assigned_guard,
        site=task.site,
        actor=actor,
        metadata={"from": previous_status, "to": status},
    )
    return task


def review_leave_request(leave_request: LeaveRequest, *, actor, status: str, note: str = "") -> LeaveRequest:
    if status not in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED}:
        raise ValidationError({"status": "Leave can only be approved, rejected, or cancelled."})
    leave_request.status = status
    leave_request.reviewed_by = actor
    leave_request.reviewed_at = timezone.now()
    leave_request.review_note = note
    leave_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    create_workflow_event(
        event_type="leave_reviewed",
        title="Leave request reviewed",
        message=f"Leave request for {leave_request.guard.full_name} was {status}.",
        obj=leave_request,
        guard=leave_request.guard,
        actor=actor,
        metadata={"status": status},
    )
    return leave_request


def _active_contract_for_assignment(assignment: ShiftAssignment) -> GuardContract | None:
    shift_date = timezone.localtime(assignment.shift.starts_at).date()
    contracts = GuardContract.objects.filter(
        site=assignment.shift.post.site,
        status=GuardContract.Status.ACTIVE,
        starts_on__lte=shift_date,
    ).filter(models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=shift_date))
    return contracts.filter(post=assignment.shift.post).first() or contracts.filter(post__isnull=True).first()


def build_timesheet_for_assignment(assignment: ShiftAssignment) -> GuardTimesheet:
    if not assignment.clocked_in_at or not assignment.clocked_out_at:
        raise ValidationError({"assignment": "Timesheets require clock-in and clock-out times."})
    if assignment.clocked_out_at <= assignment.clocked_in_at:
        raise ValidationError({"assignment": "Clock-out must be after clock-in."})

    worked_minutes = max(0, int((assignment.clocked_out_at - assignment.clocked_in_at).total_seconds() // 60))
    scheduled_minutes = max(0, int((assignment.shift.ends_at - assignment.shift.starts_at).total_seconds() // 60))
    regular_minutes = min(worked_minutes, scheduled_minutes)
    overtime_minutes = max(0, worked_minutes - scheduled_minutes)
    contract = _active_contract_for_assignment(assignment)
    pay_rate = contract.pay_rate if contract else Decimal("0.00")
    bill_rate = contract.bill_rate if contract else Decimal("0.00")
    overtime_multiplier = contract.overtime_multiplier if contract else Decimal("1.50")
    pay_amount = ((Decimal(regular_minutes) / Decimal(60)) * pay_rate) + (
        (Decimal(overtime_minutes) / Decimal(60)) * pay_rate * overtime_multiplier
    )
    bill_amount = ((Decimal(regular_minutes) / Decimal(60)) * bill_rate) + (
        (Decimal(overtime_minutes) / Decimal(60)) * bill_rate * overtime_multiplier
    )
    timesheet, _ = GuardTimesheet.objects.update_or_create(
        assignment=assignment,
        defaults={
            "guard": assignment.guard,
            "site": assignment.shift.post.site,
            "post": assignment.shift.post,
            "period_start": assignment.clocked_in_at,
            "period_end": assignment.clocked_out_at,
            "regular_minutes": regular_minutes,
            "overtime_minutes": overtime_minutes,
            "pay_amount": pay_amount.quantize(Decimal("0.01")),
            "bill_amount": bill_amount.quantize(Decimal("0.01")),
        },
    )
    create_workflow_event(
        event_type="timesheet_generated",
        title="Timesheet generated",
        message=f"Timesheet generated for {assignment.guard.full_name}.",
        obj=timesheet,
        guard=assignment.guard,
        site=assignment.shift.post.site,
        unique_key=f"timesheet_generated:{timesheet.pk}",
        metadata={"regular_minutes": regular_minutes, "overtime_minutes": overtime_minutes},
    )
    return timesheet


def review_timesheet(timesheet: GuardTimesheet, *, actor, status: str, note: str = "") -> GuardTimesheet:
    allowed = {
        GuardTimesheet.Status.DRAFT: {GuardTimesheet.Status.SUBMITTED, GuardTimesheet.Status.APPROVED, GuardTimesheet.Status.REJECTED},
        GuardTimesheet.Status.SUBMITTED: {GuardTimesheet.Status.APPROVED, GuardTimesheet.Status.REJECTED},
        GuardTimesheet.Status.APPROVED: {GuardTimesheet.Status.EXPORTED},
        GuardTimesheet.Status.REJECTED: {GuardTimesheet.Status.SUBMITTED},
        GuardTimesheet.Status.EXPORTED: set(),
    }
    _ensure_transition(timesheet.status, status, allowed, label="Timesheet")
    timesheet.status = status
    if status == GuardTimesheet.Status.APPROVED:
        timesheet.approved_by = actor
        timesheet.approved_at = timezone.now()
    if note:
        timesheet.notes = note
    timesheet.save(update_fields=["status", "approved_by", "approved_at", "notes", "updated_at"])
    create_workflow_event(
        event_type="timesheet_status_changed",
        title="Timesheet status changed",
        message=f"Timesheet for {timesheet.guard.full_name} moved to {status}.",
        obj=timesheet,
        guard=timesheet.guard,
        site=timesheet.site,
        actor=actor,
        metadata={"status": status},
    )
    return timesheet


def _next_invoice_number(site, period_start, period_end) -> str:
    prefix = f"GINV-{period_start:%Y%m%d}-{period_end:%Y%m%d}"
    count = GuardInvoice.objects.filter(invoice_number__startswith=prefix).count() + 1
    return f"{prefix}-{count:04d}"


@transaction.atomic
def generate_guard_invoice(*, site, period_start, period_end, actor=None, contract: GuardContract | None = None) -> GuardInvoice:
    if period_end < period_start:
        raise ValidationError({"period_end": "Invoice period end must be after the start."})
    timesheets = (
        GuardTimesheet.objects.select_related("guard", "post", "assignment")
        .filter(
            site=site,
            status=GuardTimesheet.Status.APPROVED,
            period_start__date__gte=period_start,
            period_start__date__lte=period_end,
            invoice_lines__isnull=True,
        )
        .order_by("period_start")
    )
    if contract:
        timesheets = timesheets.filter(models.Q(post=contract.post) if contract.post_id else models.Q(site=contract.site))
    timesheets = list(timesheets)
    if not timesheets:
        raise ValidationError({"timesheets": "No approved, uninvoiced timesheets found for this period."})

    invoice = GuardInvoice.objects.create(
        invoice_number=_next_invoice_number(site, period_start, period_end),
        site=site,
        contract=contract,
        period_start=period_start,
        period_end=period_end,
        generated_by=actor,
    )
    subtotal = Decimal("0.00")
    for sheet in timesheets:
        hours = (Decimal(sheet.total_minutes) / Decimal(60)).quantize(Decimal("0.01"))
        bill_rate = (sheet.bill_amount / hours).quantize(Decimal("0.01")) if hours else Decimal("0.00")
        line = GuardInvoiceLine.objects.create(
            invoice=invoice,
            timesheet=sheet,
            description=f"{sheet.guard.full_name} - {sheet.post.name if sheet.post else sheet.site.name} - {sheet.period_start:%Y-%m-%d}",
            quantity_hours=hours,
            bill_rate=bill_rate,
            amount=sheet.bill_amount,
            metadata={
                "timesheet_id": str(sheet.id),
                "regular_minutes": sheet.regular_minutes,
                "overtime_minutes": sheet.overtime_minutes,
            },
        )
        subtotal += line.amount
        sheet.status = GuardTimesheet.Status.EXPORTED
        sheet.export_reference = invoice.invoice_number
        sheet.save(update_fields=["status", "export_reference", "updated_at"])
    invoice.subtotal = subtotal.quantize(Decimal("0.01"))
    invoice.total = (invoice.subtotal + invoice.adjustments).quantize(Decimal("0.01"))
    invoice.save(update_fields=["subtotal", "total", "updated_at"])
    create_workflow_event(
        event_type="invoice_generated",
        title="Guard invoice generated",
        message=f"{invoice.invoice_number} generated for {site.name}.",
        obj=invoice,
        site=site,
        actor=actor,
        metadata={"subtotal": str(invoice.subtotal), "line_count": len(timesheets)},
    )
    return invoice


def transition_guard_invoice(invoice: GuardInvoice, *, status: str, actor=None) -> GuardInvoice:
    allowed = {
        GuardInvoice.Status.DRAFT: {GuardInvoice.Status.ISSUED, GuardInvoice.Status.VOID},
        GuardInvoice.Status.ISSUED: {GuardInvoice.Status.PAID, GuardInvoice.Status.VOID},
        GuardInvoice.Status.PAID: set(),
        GuardInvoice.Status.VOID: set(),
    }
    _ensure_transition(invoice.status, status, allowed, label="Invoice")
    invoice.status = status
    now = timezone.now()
    if status == GuardInvoice.Status.ISSUED:
        invoice.issued_at = invoice.issued_at or now
    if status == GuardInvoice.Status.PAID:
        invoice.paid_at = invoice.paid_at or now
    invoice.save(update_fields=["status", "issued_at", "paid_at", "updated_at"])
    create_workflow_event(
        event_type="invoice_status_changed",
        title="Guard invoice status changed",
        message=f"{invoice.invoice_number} moved to {status}.",
        obj=invoice,
        site=invoice.site,
        actor=actor,
        metadata={"status": status},
    )
    return invoice


def acknowledge_field_report(report: FieldReport, *, user, comment: str = "") -> FieldReportAcknowledgement:
    if report.status != FieldReport.Status.APPROVED or not report.visible_to_client:
        raise ValidationError({"report": "Only approved client-visible reports can be acknowledged."})
    can_acknowledge = ClientPortalAccess.objects.filter(
        user=user,
        site=report.site,
        can_acknowledge_reports=True,
    ).exists()
    if not can_acknowledge:
        raise ValidationError({"report": "You do not have acknowledgement access for this report."})
    acknowledgement, _ = FieldReportAcknowledgement.objects.update_or_create(
        report=report,
        user=user,
        defaults={"comment": comment, "acknowledged_at": timezone.now()},
    )
    create_workflow_event(
        event_type="report_acknowledged",
        title="Report acknowledged",
        message=f"{report.title} acknowledged by {user.get_username()}.",
        obj=acknowledgement,
        site=report.site,
        actor=user,
    )
    return acknowledgement


def assign_dispatch_task(task: DispatchTask, *, guard: GuardProfile, actor=None) -> DispatchTask:
    task.assigned_guard = guard
    task.save(update_fields=["assigned_guard", "updated_at"])
    if task.status == DispatchTask.Status.OPEN:
        return transition_dispatch_task(task, status=DispatchTask.Status.ASSIGNED, actor=actor)
    return task


def record_checkpoint_scan(
    *,
    patrol_round: PatrolRound,
    checkpoint: Checkpoint,
    guard: GuardProfile,
    latitude=None,
    longitude=None,
    accuracy_m=None,
    within_geofence=False,
    offline_created_at=None,
    client_scan_id: str = "",
    metadata=None,
) -> CheckpointScan:
    scan_metadata = dict(metadata or {})
    if client_scan_id:
        scan_metadata["client_scan_id"] = client_scan_id
        existing = (
            CheckpointScan.objects.filter(
                patrol_round=patrol_round,
                metadata__client_scan_id=client_scan_id,
            )
            .select_related("checkpoint", "guard")
            .first()
        )
        if existing:
            return existing

    scan = CheckpointScan.objects.create(
        patrol_round=patrol_round,
        checkpoint=checkpoint,
        guard=guard,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        within_geofence=within_geofence,
        offline_created_at=offline_created_at,
        metadata=scan_metadata,
    )
    create_workflow_event(
        event_type="checkpoint_scanned",
        title="Checkpoint scanned",
        message=f"{guard.full_name} scanned {checkpoint.name}.",
        obj=scan,
        guard=guard,
        site=checkpoint.post.site,
        metadata={"within_geofence": within_geofence, "checkpoint_id": str(checkpoint.id)},
    )
    return scan


def build_checkpoint_scan_response(scan: CheckpointScan) -> dict:
    checkpoint = scan.checkpoint
    post_orders = list(
        PostOrder.objects.filter(post=checkpoint.post, is_active=True).values("id", "title", "body")[:5]
    )
    return {
        "scan_id": str(scan.id),
        "checkpoint_instructions": checkpoint.instructions,
        "post_orders": post_orders,
    }


def suggest_nearest_guards(site, latitude: float, longitude: float, *, limit: int = 5) -> list[dict]:
    import math

    from django.utils import timezone as tz

    now = tz.now()
    assignments = (
        ShiftAssignment.objects.select_related("guard", "shift", "shift__post")
        .filter(
            shift__post__site=site,
            status=ShiftAssignment.Status.CLOCKED_IN,
            shift__starts_at__lte=now,
            shift__ends_at__gte=now,
        )
        .distinct()
    )
    results = []
    for assignment in assignments:
        ping = (
            GuardLocationPing.objects.filter(guard=assignment.guard)
            .order_by("-created_at")
            .first()
        )
        if ping is None or ping.latitude is None or ping.longitude is None:
            continue
        lat1, lon1 = float(latitude), float(longitude)
        lat2, lon2 = float(ping.latitude), float(ping.longitude)
        dist_km = 6371 * math.acos(
            min(1.0, max(-1.0, math.sin(math.radians(lat1)) * math.sin(math.radians(lat2))
                + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))))
        )
        results.append({"guard": assignment.guard, "distance_km": round(dist_km, 2), "assignment": assignment})
    results.sort(key=lambda item: item["distance_km"])
    return results[:limit]


def build_command_center_snapshot():
    from django.db.models import OuterRef, Subquery
    from django.utils import timezone as tz

    now = tz.now()
    latest_ping = GuardLocationPing.objects.filter(guard_id=OuterRef("guard_id")).order_by("-created_at")
    assignments = (
        ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
        .filter(
            status__in=[
                ShiftAssignment.Status.ASSIGNED,
                ShiftAssignment.Status.ACCEPTED,
                ShiftAssignment.Status.CLOCKED_IN,
            ],
            shift__starts_at__lte=now,
            shift__ends_at__gte=now,
        )
        .annotate(
            ping_lat=Subquery(latest_ping.values("latitude")[:1]),
            ping_lng=Subquery(latest_ping.values("longitude")[:1]),
            ping_at=Subquery(latest_ping.values("created_at")[:1]),
        )
    )
    guards = []
    for row in assignments:
        open_panic = GuardPanicAlert.objects.filter(
            guard=row.guard, status=GuardPanicAlert.Status.OPEN
        ).exists()
        active_dispatch = DispatchTask.objects.filter(
            assigned_guard=row.guard,
            status__in=[
                DispatchTask.Status.ASSIGNED,
                DispatchTask.Status.ACCEPTED,
                DispatchTask.Status.EN_ROUTE,
                DispatchTask.Status.ARRIVED,
            ],
        ).exists()
        guards.append(
            {
                "guard_id": str(row.guard_id),
                "guard_name": row.guard.full_name,
                "assignment_id": str(row.id),
                "site_id": str(row.shift.post.site_id),
                "site_name": row.shift.post.site.name,
                "post_name": row.shift.post.name,
                "post_latitude": row.shift.post.latitude,
                "post_longitude": row.shift.post.longitude,
                "site_latitude": row.shift.post.site.latitude,
                "site_longitude": row.shift.post.site.longitude,
                "latitude": row.ping_lat,
                "longitude": row.ping_lng,
                "last_ping_at": row.ping_at,
                "open_panic": open_panic,
                "active_dispatch": active_dispatch,
            }
        )
    return {
        "generated_at": now.isoformat(),
        "guards": guards,
        "open_panic_count": GuardPanicAlert.objects.filter(status=GuardPanicAlert.Status.OPEN).count(),
        "active_dispatch_count": DispatchTask.objects.exclude(
            status__in=[DispatchTask.Status.RESOLVED, DispatchTask.Status.CANCELLED]
        ).count(),
    }


def purge_old_location_pings() -> int:
    settings_row = GuardingPrivacySettings.load()
    cutoff = timezone.now() - timezone.timedelta(days=settings_row.location_ping_retention_days)
    deleted, _ = GuardLocationPing.objects.filter(created_at__lt=cutoff).delete()
    return deleted
