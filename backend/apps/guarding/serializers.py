from django.utils import timezone
from rest_framework import serializers

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    ClientPortalAccess,
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
    WelfareCheck,
)
from .services import (
    ensure_applicant_status_transition,
    ensure_assignment_matches_route,
    ensure_assignment_status_transition,
    ensure_dispatch_status_transition,
    ensure_guard_available_for_shift,
    ensure_guard_compliance_ready,
    ensure_guard_qualified_for_post,
    ensure_guard_status_transition,
    ensure_panic_alert_status_transition,
    ensure_patrol_round_status_transition,
    ensure_report_status_transition,
    ensure_shift_status_transition,
    ensure_shift_time_order,
    record_clock_event,
)


class GuardApplicantDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardApplicantDocument
        fields = "__all__"
        read_only_fields = ("id", "uploaded_by", "created_at")


class GuardApplicantEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardApplicantEducation
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class GuardApplicantEmploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardApplicantEmployment
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class GuardApplicantReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardApplicantReference
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class GuardApplicantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardApplicantProfile
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GuardApplicantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    documents = GuardApplicantDocumentSerializer(many=True, read_only=True)
    education_records = GuardApplicantEducationSerializer(many=True, read_only=True)
    employment_records = GuardApplicantEmploymentSerializer(many=True, read_only=True)
    references = GuardApplicantReferenceSerializer(many=True, read_only=True)
    profile = GuardApplicantProfileSerializer(read_only=True)

    class Meta:
        model = GuardApplicant
        fields = "__all__"
        read_only_fields = ("id", "full_name", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        if self.instance and "status" in attrs:
            ensure_applicant_status_transition(self.instance, attrs["status"])
        elif not self.instance and attrs.get("status") not in (None, GuardApplicant.Status.APPLIED):
            raise serializers.ValidationError({"status": "Applicants must start as applied."})
        return attrs


class GuardingEventLogSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = GuardingEventLog
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard_name",
            "site_name",
            "actor_name",
            "created_at",
        )

    def get_actor_name(self, obj):
        if not obj.actor_id:
            return ""
        return obj.actor.get_full_name() or obj.actor.get_username()


class GuardCredentialSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = GuardCredential
        fields = "__all__"
        read_only_fields = ("id", "is_expired", "created_at", "updated_at")


class GuardDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardDocument
        fields = "__all__"
        read_only_fields = ("id", "uploaded_by", "created_at")


class GuardTrainingRecordSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

    class Meta:
        model = GuardTrainingRecord
        fields = "__all__"
        read_only_fields = ("id", "guard_name", "created_at", "updated_at")


class GuardEquipmentIssueSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

    class Meta:
        model = GuardEquipmentIssue
        fields = "__all__"
        read_only_fields = ("id", "guard_name", "issued_by", "created_at", "updated_at")


class GuardOffboardingChecklistSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = GuardOffboardingChecklist
        fields = "__all__"
        read_only_fields = ("id", "guard_name", "is_complete", "completed_by", "completed_at", "created_at", "updated_at")


class GuardProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    credentials = GuardCredentialSerializer(many=True, read_only=True)
    documents = GuardDocumentSerializer(many=True, read_only=True)
    training_records = GuardTrainingRecordSerializer(many=True, read_only=True)
    equipment_issues = GuardEquipmentIssueSerializer(many=True, read_only=True)

    class Meta:
        model = GuardProfile
        fields = "__all__"
        read_only_fields = ("id", "full_name", "created_at", "updated_at")

    def validate(self, attrs):
        if self.instance and "status" in attrs:
            ensure_guard_status_transition(self.instance, attrs["status"])
        status_value = attrs.get("status", getattr(self.instance, "status", None))
        termination_date = attrs.get("termination_date", getattr(self.instance, "termination_date", None))
        if status_value == GuardProfile.Status.TERMINATED and termination_date is None:
            attrs["termination_date"] = timezone.localdate()
        if status_value == GuardProfile.Status.ACTIVE:
            current_status = getattr(self.instance, "status", None)
            if not self.instance or current_status != GuardProfile.Status.ACTIVE:
                guard_check = self.instance or GuardProfile()
                for field in (
                    "emergency_contact_name",
                    "emergency_contact_phone",
                    "employee_number",
                    "first_name",
                    "last_name",
                ):
                    if field in attrs:
                        setattr(guard_check, field, attrs[field])
                ensure_guard_compliance_ready(guard_check)
        return attrs


class PostOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostOrder
        fields = "__all__"
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class GuardPostSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = GuardPost
        fields = "__all__"
        read_only_fields = ("id", "site_name", "created_at", "updated_at")


class GuardContractSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    post_name = serializers.CharField(source="post.name", read_only=True)

    class Meta:
        model = GuardContract
        fields = "__all__"
        read_only_fields = ("id", "site_name", "post_name", "created_at", "updated_at")

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError({"ends_on": "Contract end date must be after the start date."})
        site = attrs.get("site", getattr(self.instance, "site", None))
        post = attrs.get("post", getattr(self.instance, "post", None))
        if site and post and post.site_id != site.id:
            raise serializers.ValidationError({"post": "Contract post must belong to the contract site."})
        return attrs


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    post_name = serializers.CharField(source="shift.post.name", read_only=True)
    site_name = serializers.CharField(source="shift.post.site.name", read_only=True)
    starts_at = serializers.DateTimeField(source="shift.starts_at", read_only=True)
    ends_at = serializers.DateTimeField(source="shift.ends_at", read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard_name",
            "post_name",
            "site_name",
            "starts_at",
            "ends_at",
            "assigned_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        guard = attrs.get("guard", getattr(self.instance, "guard", None))
        shift = attrs.get("shift", getattr(self.instance, "shift", None))
        if guard and guard.status != GuardProfile.Status.ACTIVE:
            raise serializers.ValidationError({"guard": "Only active guards can be assigned to shifts."})
        if guard and (not self.instance or getattr(self.instance, "guard_id", None) != guard.pk):
            ensure_guard_compliance_ready(guard)
        if guard and shift:
            ensure_guard_available_for_shift(guard, shift, assignment=self.instance)
            ensure_guard_qualified_for_post(guard, shift.post)
        if self.instance and "status" in attrs:
            ensure_assignment_status_transition(self.instance, attrs["status"])
        return attrs


class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True)
    target_guard_name = serializers.CharField(source="target_guard.full_name", read_only=True)
    site_name = serializers.CharField(source="assignment.shift.post.site.name", read_only=True)
    post_name = serializers.CharField(source="assignment.shift.post.name", read_only=True)

    class Meta:
        model = ShiftSwapRequest
        fields = "__all__"
        read_only_fields = (
            "id",
            "requested_by_name",
            "requested_by",
            "target_guard_name",
            "site_name",
            "post_name",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        assignment = attrs.get("assignment", getattr(self.instance, "assignment", None))
        requested_by = attrs.get("requested_by", getattr(self.instance, "requested_by", None))
        target_guard = attrs.get("target_guard", getattr(self.instance, "target_guard", None))
        if assignment and requested_by and assignment.guard_id != requested_by.id:
            raise serializers.ValidationError({"requested_by": "The requesting guard must own the assignment."})
        if target_guard and assignment:
            ensure_guard_available_for_shift(target_guard, assignment.shift)
            ensure_guard_qualified_for_post(target_guard, assignment.shift.post)
        return attrs


class GuardAvailabilitySerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

    class Meta:
        model = GuardAvailability
        fields = "__all__"
        read_only_fields = ("id", "guard_name", "created_by", "created_at")

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        ensure_shift_time_order(starts_at, ends_at)
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("id", "guard_name", "reviewed_by", "reviewed_at", "created_at", "updated_at")

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        ensure_shift_time_order(starts_at, ends_at)
        return attrs


class ShiftTemplateSerializer(serializers.ModelSerializer):
    post_name = serializers.CharField(source="post.name", read_only=True)
    site_name = serializers.CharField(source="post.site.name", read_only=True)

    class Meta:
        model = ShiftTemplate
        fields = "__all__"
        read_only_fields = ("id", "post_name", "site_name", "created_at", "updated_at")


class ShiftSerializer(serializers.ModelSerializer):
    post_name = serializers.CharField(source="post.name", read_only=True)
    site_name = serializers.CharField(source="post.site.name", read_only=True)
    assignments = ShiftAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = ("id", "post_name", "site_name", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        ensure_shift_time_order(starts_at, ends_at)
        if self.instance and "status" in attrs:
            ensure_shift_status_transition(self.instance, attrs["status"])
        return attrs


class ClockEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClockEvent
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        assignment = attrs.get("assignment", getattr(self.instance, "assignment", None))
        event_type = attrs.get("event_type", getattr(self.instance, "event_type", None))
        if not assignment:
            return attrs
        if assignment.status in {ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW}:
            raise serializers.ValidationError({"assignment": "This assignment is closed."})
        if event_type == ClockEvent.EventType.CLOCK_IN and assignment.clocked_in_at:
            raise serializers.ValidationError({"event_type": "This assignment is already clocked in."})
        if event_type == ClockEvent.EventType.CLOCK_OUT and not assignment.clocked_in_at:
            raise serializers.ValidationError({"event_type": "Cannot clock out before clocking in."})
        return attrs

    def create(self, validated_data):
        return record_clock_event(
            assignment=validated_data["assignment"],
            event_type=validated_data["event_type"],
            latitude=validated_data.get("latitude"),
            longitude=validated_data.get("longitude"),
            accuracy_m=validated_data.get("accuracy_m"),
            within_geofence=validated_data.get("within_geofence", False),
            device_timestamp=validated_data.get("device_timestamp"),
        )


class CheckpointSerializer(serializers.ModelSerializer):
    post_name = serializers.CharField(source="post.name", read_only=True)

    class Meta:
        model = Checkpoint
        fields = "__all__"
        read_only_fields = ("id", "post_name", "created_at", "updated_at")


class PatrolRouteCheckpointSerializer(serializers.ModelSerializer):
    checkpoint_name = serializers.CharField(source="checkpoint.name", read_only=True)
    checkpoint_code = serializers.CharField(source="checkpoint.code", read_only=True)

    class Meta:
        model = PatrolRouteCheckpoint
        fields = "__all__"
        read_only_fields = ("checkpoint_name", "checkpoint_code")

    def validate(self, attrs):
        route = attrs.get("route", getattr(self.instance, "route", None))
        checkpoint = attrs.get("checkpoint", getattr(self.instance, "checkpoint", None))
        if route and checkpoint and route.post_id != checkpoint.post_id:
            raise serializers.ValidationError({"checkpoint": "Checkpoint must belong to the same post as the route."})
        return attrs


class PatrolRouteSerializer(serializers.ModelSerializer):
    post_name = serializers.CharField(source="post.name", read_only=True)
    route_checkpoints = PatrolRouteCheckpointSerializer(source="patrolroutecheckpoint_set", many=True, read_only=True)

    class Meta:
        model = PatrolRoute
        fields = "__all__"
        read_only_fields = ("id", "post_name", "route_checkpoints", "created_at", "updated_at")


class PatrolRoundSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = PatrolRound
        fields = "__all__"
        read_only_fields = ("id", "route_name", "created_at", "updated_at")

    def validate(self, attrs):
        scheduled_start = attrs.get("scheduled_start", getattr(self.instance, "scheduled_start", None))
        scheduled_end = attrs.get("scheduled_end", getattr(self.instance, "scheduled_end", None))
        ensure_shift_time_order(scheduled_start, scheduled_end)
        patrol_round = self.instance or PatrolRound(**attrs)
        for key, value in attrs.items():
            setattr(patrol_round, key, value)
        ensure_assignment_matches_route(patrol_round)
        if self.instance and "status" in attrs:
            ensure_patrol_round_status_transition(self.instance, attrs["status"])
        return attrs


class PatrolRoundMobileSerializer(PatrolRoundSerializer):
    route = PatrolRouteSerializer(read_only=True)
    site_name = serializers.CharField(source="route.post.site.name", read_only=True)
    post_name = serializers.CharField(source="route.post.name", read_only=True)

    class Meta(PatrolRoundSerializer.Meta):
        read_only_fields = PatrolRoundSerializer.Meta.read_only_fields + (
            "route",
            "site_name",
            "post_name",
        )


class CheckpointScanSerializer(serializers.ModelSerializer):
    checkpoint_name = serializers.CharField(source="checkpoint.name", read_only=True)
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    client_scan_id = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = CheckpointScan
        fields = "__all__"
        read_only_fields = ("id", "checkpoint_name", "guard_name", "guard", "created_at")

    def validate(self, attrs):
        patrol_round = attrs.get("patrol_round", getattr(self.instance, "patrol_round", None))
        checkpoint = attrs.get("checkpoint", getattr(self.instance, "checkpoint", None))
        if patrol_round and checkpoint:
            route_checkpoint_exists = patrol_round.route.patrolroutecheckpoint_set.filter(checkpoint=checkpoint).exists()
            if not route_checkpoint_exists:
                raise serializers.ValidationError({"checkpoint": "Checkpoint is not part of this patrol route."})
        return attrs

    def create(self, validated_data):
        client_scan_id = validated_data.pop("client_scan_id", "")
        metadata = dict(validated_data.get("metadata") or {})
        if client_scan_id:
            metadata["client_scan_id"] = client_scan_id
        validated_data["metadata"] = metadata
        return super().create(validated_data)


class FieldReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldReportAttachment
        fields = "__all__"
        read_only_fields = ("id", "uploaded_at")


class FieldReportAcknowledgementSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    report_title = serializers.CharField(source="report.title", read_only=True)

    class Meta:
        model = FieldReportAcknowledgement
        fields = "__all__"
        read_only_fields = ("id", "username", "report_title", "acknowledged_at")


class ReportTemplateSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = ReportTemplate
        fields = "__all__"
        read_only_fields = ("id", "site_name", "created_by", "created_at", "updated_at")


class FieldReportSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    post_name = serializers.CharField(source="post.name", read_only=True)
    attachments = FieldReportAttachmentSerializer(many=True, read_only=True)
    client_acknowledgements = FieldReportAcknowledgementSerializer(many=True, read_only=True)

    class Meta:
        model = FieldReport
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard_name",
            "site_name",
            "post_name",
            "attachments",
            "client_acknowledgements",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "site": {"required": False},
            "post": {"required": False},
            "guard": {"required": False},
        }

    def validate(self, attrs):
        assignment = attrs.get("assignment", getattr(self.instance, "assignment", None))
        if assignment and not attrs.get("site"):
            attrs["site"] = assignment.shift.post.site
        if assignment and not attrs.get("post"):
            attrs["post"] = assignment.shift.post
        if not attrs.get("site") and not getattr(self.instance, "site_id", None):
            raise serializers.ValidationError({"site": "Site is required when no assignment is provided."})
        site = attrs.get("site", getattr(self.instance, "site", None))
        post = attrs.get("post", getattr(self.instance, "post", None))
        if assignment:
            shift_post = assignment.shift.post
            if site and site.id != shift_post.site_id:
                raise serializers.ValidationError({"site": "Report site must match the assignment site."})
            if post and post.id != shift_post.id:
                raise serializers.ValidationError({"post": "Report post must match the assignment post."})
        if self.instance and "status" in attrs:
            ensure_report_status_transition(self.instance, attrs["status"])
        elif not self.instance and attrs.get("status") in {FieldReport.Status.APPROVED, FieldReport.Status.REJECTED}:
            raise serializers.ValidationError({"status": "Reports must be reviewed before approval or rejection."})
        return attrs


class GuardLocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardLocationPing
        fields = "__all__"
        read_only_fields = ("id", "guard", "created_at")

    def validate(self, attrs):
        assignment = attrs.get("assignment")
        if assignment and assignment.status not in {ShiftAssignment.Status.ACCEPTED, ShiftAssignment.Status.CLOCKED_IN}:
            raise serializers.ValidationError({"assignment": "Location pings require an accepted or clocked-in assignment."})
        return attrs


class GuardTimesheetSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    post_name = serializers.CharField(source="post.name", read_only=True)
    total_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = GuardTimesheet
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard_name",
            "site_name",
            "post_name",
            "total_minutes",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        )


class GuardInvoiceLineSerializer(serializers.ModelSerializer):
    timesheet_guard_name = serializers.CharField(source="timesheet.guard.full_name", read_only=True)

    class Meta:
        model = GuardInvoiceLine
        fields = "__all__"
        read_only_fields = ("id", "timesheet_guard_name", "created_at")


class GuardInvoiceSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    contract_name = serializers.CharField(source="contract.name", read_only=True)
    lines = GuardInvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = GuardInvoice
        fields = "__all__"
        read_only_fields = (
            "id",
            "site_name",
            "contract_name",
            "invoice_number",
            "subtotal",
            "total",
            "generated_by",
            "issued_at",
            "paid_at",
            "created_at",
            "updated_at",
            "lines",
        )


class ClientPortalAccessSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ClientPortalAccess
        fields = "__all__"
        read_only_fields = ("id", "site_name", "username", "created_at")


class WelfareCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = WelfareCheck
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class WelfareCheckMobileSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="assignment.shift.post.site.name", read_only=True)
    post_name = serializers.CharField(source="assignment.shift.post.name", read_only=True)
    assignment_id = serializers.UUIDField(source="assignment.id", read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = WelfareCheck
        fields = (
            "id",
            "assignment_id",
            "due_at",
            "responded_at",
            "status",
            "response_note",
            "site_name",
            "post_name",
            "is_overdue",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_overdue(self, obj):
        from django.utils import timezone

        return obj.status == WelfareCheck.Status.PENDING and obj.due_at <= timezone.now()


class GuardPanicAlertSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = GuardPanicAlert
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard",
            "guard_name",
            "site_name",
            "acknowledged_by",
            "acknowledged_at",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        assignment = attrs.get("assignment", getattr(self.instance, "assignment", None))
        site = attrs.get("site", getattr(self.instance, "site", None))
        if assignment and site and assignment.shift.post.site_id != site.id:
            raise serializers.ValidationError({"site": "Panic alert site must match the assignment site."})
        if self.instance and "status" in attrs:
            ensure_panic_alert_status_transition(self.instance, attrs["status"])
        elif not self.instance and attrs.get("status") not in (None, GuardPanicAlert.Status.OPEN):
            raise serializers.ValidationError({"status": "Panic alerts must start open."})
        return attrs


class DispatchTaskSerializer(serializers.ModelSerializer):
    assigned_guard_name = serializers.CharField(source="assigned_guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = DispatchTask
        fields = "__all__"
        read_only_fields = (
            "id",
            "assigned_guard_name",
            "site_name",
            "created_by",
            "assigned_at",
            "accepted_at",
            "en_route_at",
            "arrived_at",
            "resolved_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        site = attrs.get("site", getattr(self.instance, "site", None))
        alarm_event = attrs.get("alarm_event", getattr(self.instance, "alarm_event", None))
        emergency_request = attrs.get("emergency_request", getattr(self.instance, "emergency_request", None))
        panic_alert = attrs.get("panic_alert", getattr(self.instance, "panic_alert", None))
        source_sites = [
            source_site
            for source_site in [
                getattr(alarm_event, "site", None),
                getattr(emergency_request, "site", None),
                getattr(panic_alert, "site", None),
            ]
            if source_site is not None
        ]
        if site and any(source_site.id != site.id for source_site in source_sites):
            raise serializers.ValidationError({"site": "Dispatch site must match linked alarm, emergency, or panic source."})
        if not site and source_sites:
            attrs["site"] = source_sites[0]
        if self.instance and "status" in attrs:
            ensure_dispatch_status_transition(self.instance, attrs["status"])
        elif not self.instance and attrs.get("status") not in (None, DispatchTask.Status.OPEN, DispatchTask.Status.ASSIGNED):
            raise serializers.ValidationError({"status": "Dispatch tasks must start open or assigned."})
        assigned_guard = attrs.get("assigned_guard", getattr(self.instance, "assigned_guard", None))
        if attrs.get("status") == DispatchTask.Status.ASSIGNED and assigned_guard is None:
            raise serializers.ValidationError({"assigned_guard": "A guard is required for assigned dispatch tasks."})
        return attrs
