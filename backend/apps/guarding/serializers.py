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


class GuardApplicantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = GuardApplicant
        fields = "__all__"
        read_only_fields = ("id", "full_name", "created_by", "created_at", "updated_at")


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


class ShiftSerializer(serializers.ModelSerializer):
    post_name = serializers.CharField(source="post.name", read_only=True)
    site_name = serializers.CharField(source="post.site.name", read_only=True)
    assignments = ShiftAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = ("id", "post_name", "site_name", "created_by", "created_at", "updated_at")


class ClockEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClockEvent
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        clock_event = super().create(validated_data)
        assignment = clock_event.assignment
        now = clock_event.created_at or timezone.now()
        if clock_event.event_type == ClockEvent.EventType.CLOCK_IN:
            assignment.status = ShiftAssignment.Status.CLOCKED_IN
            assignment.clocked_in_at = assignment.clocked_in_at or now
            assignment.save(update_fields=["status", "clocked_in_at", "updated_at"])
        elif clock_event.event_type == ClockEvent.EventType.CLOCK_OUT:
            assignment.status = ShiftAssignment.Status.CLOCKED_OUT
            assignment.clocked_out_at = now
            assignment.save(update_fields=["status", "clocked_out_at", "updated_at"])
        return clock_event


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


class CheckpointScanSerializer(serializers.ModelSerializer):
    checkpoint_name = serializers.CharField(source="checkpoint.name", read_only=True)
    guard_name = serializers.CharField(source="guard.full_name", read_only=True)

    class Meta:
        model = CheckpointScan
        fields = "__all__"
        read_only_fields = ("id", "checkpoint_name", "guard_name", "guard", "created_at")


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


class GuardLocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardLocationPing
        fields = "__all__"
        read_only_fields = ("id", "guard", "created_at")


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

