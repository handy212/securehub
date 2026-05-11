from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    DispatchTask,
    FieldReport,
    GuardApplicant,
    GuardCredential,
    GuardDocument,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRound,
    PostOrder,
    Shift,
    ShiftAssignment,
    WelfareCheck,
)
from .serializers import (
    CheckpointScanSerializer,
    CheckpointSerializer,
    ClockEventSerializer,
    DispatchTaskSerializer,
    FieldReportSerializer,
    GuardApplicantSerializer,
    GuardCredentialSerializer,
    GuardDocumentSerializer,
    GuardLocationPingSerializer,
    GuardPanicAlertSerializer,
    GuardPostSerializer,
    GuardProfileSerializer,
    PatrolRouteSerializer,
    PatrolRoundSerializer,
    PostOrderSerializer,
    ShiftAssignmentSerializer,
    ShiftSerializer,
    WelfareCheckSerializer,
)


def get_guard_for_user(user):
    guard = GuardProfile.objects.filter(user=user).first()
    if guard is None:
        raise PermissionDenied("Your account is not linked to a guard profile.")
    return guard


class StaffGuardingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]


class GuardApplicantViewSet(StaffGuardingViewSet):
    queryset = GuardApplicant.objects.select_related("created_by", "hired_guard")
    serializer_class = GuardApplicantSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GuardProfileViewSet(StaffGuardingViewSet):
    queryset = GuardProfile.objects.select_related("user", "supervisor").prefetch_related("credentials", "documents")
    serializer_class = GuardProfileSerializer


class GuardCredentialViewSet(StaffGuardingViewSet):
    queryset = GuardCredential.objects.select_related("guard")
    serializer_class = GuardCredentialSerializer


class GuardDocumentViewSet(StaffGuardingViewSet):
    queryset = GuardDocument.objects.select_related("guard", "uploaded_by")
    serializer_class = GuardDocumentSerializer

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class GuardPostViewSet(StaffGuardingViewSet):
    queryset = GuardPost.objects.select_related("site", "supervisor")
    serializer_class = GuardPostSerializer


class PostOrderViewSet(StaffGuardingViewSet):
    queryset = PostOrder.objects.select_related("post", "created_by")
    serializer_class = PostOrderSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ShiftViewSet(StaffGuardingViewSet):
    queryset = Shift.objects.select_related("post", "post__site", "created_by").prefetch_related("assignments")
    serializer_class = ShiftSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ShiftAssignmentViewSet(StaffGuardingViewSet):
    queryset = ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard", "assigned_by")
    serializer_class = ShiftAssignmentSerializer

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class ClockEventViewSet(StaffGuardingViewSet):
    queryset = ClockEvent.objects.select_related("assignment", "assignment__guard", "assignment__shift")
    serializer_class = ClockEventSerializer


class CheckpointViewSet(StaffGuardingViewSet):
    queryset = Checkpoint.objects.select_related("post", "post__site")
    serializer_class = CheckpointSerializer


class PatrolRouteViewSet(StaffGuardingViewSet):
    queryset = PatrolRoute.objects.select_related("post", "post__site").prefetch_related("patrolroutecheckpoint_set")
    serializer_class = PatrolRouteSerializer


class PatrolRoundViewSet(StaffGuardingViewSet):
    queryset = PatrolRound.objects.select_related("route", "route__post", "assignment", "assignment__guard")
    serializer_class = PatrolRoundSerializer


class CheckpointScanViewSet(StaffGuardingViewSet):
    queryset = CheckpointScan.objects.select_related("patrol_round", "checkpoint", "guard")
    serializer_class = CheckpointScanSerializer


class FieldReportViewSet(StaffGuardingViewSet):
    queryset = FieldReport.objects.select_related("site", "post", "assignment", "guard", "reviewed_by").prefetch_related("attachments")
    serializer_class = FieldReportSerializer


class GuardLocationPingViewSet(StaffGuardingViewSet):
    queryset = GuardLocationPing.objects.select_related("guard", "assignment")
    serializer_class = GuardLocationPingSerializer


class WelfareCheckViewSet(StaffGuardingViewSet):
    queryset = WelfareCheck.objects.select_related("assignment", "assignment__guard")
    serializer_class = WelfareCheckSerializer


class GuardPanicAlertViewSet(StaffGuardingViewSet):
    queryset = GuardPanicAlert.objects.select_related("guard", "assignment", "site", "acknowledged_by", "resolved_by")
    serializer_class = GuardPanicAlertSerializer


class DispatchTaskViewSet(StaffGuardingViewSet):
    queryset = DispatchTask.objects.select_related(
        "site",
        "assigned_guard",
        "alarm_event",
        "emergency_request",
        "panic_alert",
        "created_by",
    )
    serializer_class = DispatchTaskSerializer

    def perform_create(self, serializer):
        assigned_guard = serializer.validated_data.get("assigned_guard")
        serializer.save(
            created_by=self.request.user,
            assigned_at=timezone.now() if assigned_guard else None,
        )


class MyShiftAssignmentListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShiftAssignmentSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard").filter(
            guard=guard
        )


class MyClockEventCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assignment_id):
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        serializer = ClockEventSerializer(data={**request.data, "assignment": assignment.id})
        serializer.is_valid(raise_exception=True)
        clock_event = serializer.save()
        return Response(ClockEventSerializer(clock_event).data, status=status.HTTP_201_CREATED)


class MyCheckpointScanCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, patrol_round_id):
        guard = get_guard_for_user(request.user)
        patrol_round = get_object_or_404(
            PatrolRound.objects.select_related("assignment"),
            id=patrol_round_id,
            assignment__guard=guard,
        )
        serializer = CheckpointScanSerializer(data={**request.data, "patrol_round": patrol_round.id})
        serializer.is_valid(raise_exception=True)
        checkpoint = serializer.validated_data["checkpoint"]
        if checkpoint.post_id != patrol_round.route.post_id:
            raise ValidationError({"checkpoint": "Checkpoint does not belong to this patrol route post."})
        scan = serializer.save(guard=guard)
        if patrol_round.status == PatrolRound.Status.SCHEDULED:
            patrol_round.status = PatrolRound.Status.IN_PROGRESS
            patrol_round.started_at = scan.scanned_at
            patrol_round.save(update_fields=["status", "started_at", "updated_at"])
        return Response(CheckpointScanSerializer(scan).data, status=status.HTTP_201_CREATED)


class MyFieldReportListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FieldReportSerializer

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return FieldReport.objects.select_related("site", "post", "assignment", "guard").filter(guard=guard)

    def perform_create(self, serializer):
        guard = get_guard_for_user(self.request.user)
        assignment = serializer.validated_data.get("assignment")
        if assignment is not None and assignment.guard_id != guard.id:
            raise ValidationError({"assignment": "Assignment does not belong to the current guard."})
        if assignment is not None:
            serializer.save(guard=guard, site=assignment.shift.post.site, post=assignment.shift.post)
        else:
            serializer.save(guard=guard)


class MyLocationPingCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        guard = get_guard_for_user(request.user)
        serializer = GuardLocationPingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.validated_data.get("assignment")
        if assignment is not None and assignment.guard_id != guard.id:
            raise ValidationError({"assignment": "Assignment does not belong to the current guard."})
        ping = serializer.save(guard=guard)
        return Response(GuardLocationPingSerializer(ping).data, status=status.HTTP_201_CREATED)


class MyPanicAlertCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        guard = get_guard_for_user(request.user)
        serializer = GuardPanicAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.validated_data.get("assignment")
        if assignment is not None and assignment.guard_id != guard.id:
            raise ValidationError({"assignment": "Assignment does not belong to the current guard."})
        site = serializer.validated_data.get("site")
        if site is None and assignment is not None:
            site = assignment.shift.post.site
        alert = serializer.save(guard=guard, site=site)
        return Response(GuardPanicAlertSerializer(alert).data, status=status.HTTP_201_CREATED)

