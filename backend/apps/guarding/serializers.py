from django.utils import timezone
from rest_framework import serializers

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    DispatchTask,
    FieldReport,
    FieldReportAttachment,
    GuardApplicant,
    GuardCredential,
    GuardDocument,
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    PostOrder,
    Shift,
    ShiftAssignment,
    WelfareCheck,
)
from .services import (
    ensure_applicant_status_transition,
    ensure_assignment_matches_route,
    ensure_assignment_status_transition,
    ensure_dispatch_status_transition,
    ensure_guard_status_transition,
    ensure_panic_alert_status_transition,
    ensure_patrol_round_status_transition,
    ensure_report_status_transition,
    ensure_shift_status_transition,
    ensure_shift_time_order,
    record_clock_event,
)


class GuardApplicantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

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


class GuardProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    credentials = GuardCredentialSerializer(many=True, read_only=True)
    documents = GuardDocumentSerializer(many=True, read_only=True)

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
        if guard and guard.status != GuardProfile.Status.ACTIVE:
            raise serializers.ValidationError({"guard": "Only active guards can be assigned to shifts."})
        if self.instance and "status" in attrs:
            ensure_assignment_status_transition(self.instance, attrs["status"])
        return attrs


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

    class Meta:
        model = PatrolRouteCheckpoint
        fields = "__all__"

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


class CheckpointScanSerializer(serializers.ModelSerializer):
    checkpoint_name = serializers.CharField(source="checkpoint.name", read_only=True)
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

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


class FieldReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldReportAttachment
        fields = "__all__"
        read_only_fields = ("id", "uploaded_at")


class FieldReportSerializer(serializers.ModelSerializer):
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    post_name = serializers.CharField(source="post.name", read_only=True)
    attachments = FieldReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FieldReport
        fields = "__all__"
        read_only_fields = (
            "id",
            "guard_name",
            "site_name",
            "post_name",
            "attachments",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        assignment = attrs.get("assignment", getattr(self.instance, "assignment", None))
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


class WelfareCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = WelfareCheck
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


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
