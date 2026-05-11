from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, permissions, serializers, status, viewsets
from rest_framework.decorators import action
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
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRound,
    PatrolRouteCheckpoint,
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
    GuardingEventLogSerializer,
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
    PatrolRouteCheckpointSerializer,
)
from .services import (
    accept_assignment,
    acknowledge_panic_alert,
    complete_patrol_round,
    decline_assignment,
    hire_applicant,
    mark_assignment_no_show,
    respond_to_welfare_check,
    resolve_panic_alert,
    review_field_report,
    transition_dispatch_task,
    transition_patrol_round,
    transition_shift,
)


def get_guard_for_user(user):
    guard = GuardProfile.objects.filter(user=user).first()
    if guard is None:
        raise PermissionDenied("Your account is not linked to a guard profile.")
    return guard


class StaffGuardingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    query_param_filters = {}

    def get_schema_operation_parameters(self):
        parameters = super().get_schema_operation_parameters()
        for name in self.query_param_filters:
            parameters.append(
                {
                    "name": name,
                    "required": False,
                    "in": "query",
                    "description": f"Filter by {name.replace('_', ' ')}.",
                    "schema": {"type": "string"},
                }
            )
        return parameters

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        for param, field_name in getattr(self, "query_param_filters", {}).items():
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                queryset = queryset.filter(**{field_name: value})
        return queryset


class GuardApplicantViewSet(StaffGuardingViewSet):
    queryset = GuardApplicant.objects.select_related("created_by", "hired_guard")
    serializer_class = GuardApplicantSerializer
    search_fields = ["first_name", "last_name", "email", "phone_number", "source"]
    ordering_fields = ["created_at", "updated_at", "first_name", "last_name", "status"]
    ordering = ["-created_at"]
    query_param_filters = {"status": "status"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def hire(self, request, pk=None):
        class HireSerializer(serializers.Serializer):
            employee_number = serializers.CharField(max_length=64)

        serializer = HireSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guard = hire_applicant(
            self.get_object(),
            employee_number=serializer.validated_data["employee_number"],
            actor=request.user,
        )
        return Response(GuardProfileSerializer(guard).data, status=status.HTTP_201_CREATED)


class GuardingEventLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = GuardingEventLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    queryset = GuardingEventLog.objects.select_related("guard", "site", "actor")
    search_fields = ["event_type", "title", "message", "guard__first_name", "guard__last_name", "site__name"]
    ordering_fields = ["created_at", "severity", "event_type", "source"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        for param in ["severity", "source", "event_type", "object_label", "object_id"]:
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                queryset = queryset.filter(**{param: value})
        return queryset


class GuardProfileViewSet(StaffGuardingViewSet):
    queryset = GuardProfile.objects.select_related("user", "supervisor").prefetch_related("credentials", "documents")
    serializer_class = GuardProfileSerializer
    search_fields = ["employee_number", "first_name", "last_name", "email", "phone_number"]
    ordering_fields = ["employee_number", "first_name", "last_name", "hire_date", "status", "created_at"]
    ordering = ["last_name", "first_name"]
    query_param_filters = {"status": "status", "supervisor": "supervisor_id"}


class GuardCredentialViewSet(StaffGuardingViewSet):
    queryset = GuardCredential.objects.select_related("guard")
    serializer_class = GuardCredentialSerializer
    search_fields = ["name", "issuing_authority", "reference_number", "guard__first_name", "guard__last_name"]
    ordering_fields = ["expires_on", "issued_on", "name", "credential_type", "created_at"]
    ordering = ["expires_on", "name"]
    query_param_filters = {"guard": "guard_id", "credential_type": "credential_type", "verified": "verified"}


class GuardDocumentViewSet(StaffGuardingViewSet):
    queryset = GuardDocument.objects.select_related("guard", "uploaded_by")
    serializer_class = GuardDocumentSerializer
    search_fields = ["title", "reference_number", "guard__first_name", "guard__last_name"]
    ordering_fields = ["expires_on", "created_at", "title", "document_type"]
    ordering = ["-created_at"]
    query_param_filters = {"guard": "guard_id", "document_type": "document_type"}

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class GuardPostViewSet(StaffGuardingViewSet):
    queryset = GuardPost.objects.select_related("site", "supervisor")
    serializer_class = GuardPostSerializer
    search_fields = ["name", "code", "site__name", "description"]
    ordering_fields = ["name", "site__name", "created_at", "is_active"]
    ordering = ["site__name", "name"]
    query_param_filters = {"site": "site_id", "is_active": "is_active", "supervisor": "supervisor_id"}


class PostOrderViewSet(StaffGuardingViewSet):
    queryset = PostOrder.objects.select_related("post", "created_by")
    serializer_class = PostOrderSerializer
    search_fields = ["title", "body", "post__name", "post__site__name"]
    ordering_fields = ["created_at", "effective_from", "effective_until", "title", "is_active"]
    ordering = ["post", "-created_at"]
    query_param_filters = {"post": "post_id", "is_active": "is_active"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ShiftViewSet(StaffGuardingViewSet):
    queryset = Shift.objects.select_related("post", "post__site", "created_by").prefetch_related("assignments")
    serializer_class = ShiftSerializer
    search_fields = ["post__name", "post__site__name", "notes"]
    ordering_fields = ["starts_at", "ends_at", "status", "required_guards", "created_at"]
    ordering = ["-starts_at"]
    query_param_filters = {"post": "post_id", "site": "post__site_id", "status": "status"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        class ShiftTransitionSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=Shift.Status.choices)

        serializer = ShiftTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = transition_shift(self.get_object(), serializer.validated_data["status"])
        return Response(self.get_serializer(shift).data)


class ShiftAssignmentViewSet(StaffGuardingViewSet):
    queryset = ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard", "assigned_by")
    serializer_class = ShiftAssignmentSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name", "shift__post__name", "shift__post__site__name"]
    ordering_fields = ["shift__starts_at", "status", "created_at", "accepted_at", "clocked_in_at", "clocked_out_at"]
    ordering = ["shift__starts_at", "guard__last_name"]
    query_param_filters = {"guard": "guard_id", "shift": "shift_id", "post": "shift__post_id", "site": "shift__post__site_id", "status": "status"}

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = accept_assignment(self.get_object())
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        assignment = decline_assignment(self.get_object(), note=request.data.get("note", ""))
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        assignment = mark_assignment_no_show(self.get_object(), note=request.data.get("note", ""))
        return Response(self.get_serializer(assignment).data)


class ClockEventViewSet(StaffGuardingViewSet):
    queryset = ClockEvent.objects.select_related("assignment", "assignment__guard", "assignment__shift")
    serializer_class = ClockEventSerializer
    search_fields = ["assignment__guard__employee_number", "assignment__guard__first_name", "assignment__guard__last_name"]
    ordering_fields = ["created_at", "event_type", "within_geofence"]
    ordering = ["-created_at"]
    query_param_filters = {"assignment": "assignment_id", "event_type": "event_type", "within_geofence": "within_geofence"}


class CheckpointViewSet(StaffGuardingViewSet):
    queryset = Checkpoint.objects.select_related("post", "post__site")
    serializer_class = CheckpointSerializer
    search_fields = ["name", "code", "post__name", "post__site__name"]
    ordering_fields = ["name", "checkpoint_type", "is_active", "created_at"]
    ordering = ["post", "name"]
    query_param_filters = {"post": "post_id", "site": "post__site_id", "checkpoint_type": "checkpoint_type", "is_active": "is_active"}


class PatrolRouteViewSet(StaffGuardingViewSet):
    queryset = PatrolRoute.objects.select_related("post", "post__site").prefetch_related("patrolroutecheckpoint_set")
    serializer_class = PatrolRouteSerializer
    search_fields = ["name", "description", "post__name", "post__site__name"]
    ordering_fields = ["name", "expected_duration_minutes", "is_active", "created_at"]
    ordering = ["post", "name"]
    query_param_filters = {"post": "post_id", "site": "post__site_id", "is_active": "is_active"}


class PatrolRouteCheckpointViewSet(StaffGuardingViewSet):
    queryset = PatrolRouteCheckpoint.objects.select_related("route", "route__post", "checkpoint")
    serializer_class = PatrolRouteCheckpointSerializer
    search_fields = ["route__name", "checkpoint__name", "checkpoint__code"]
    ordering_fields = ["sequence"]
    ordering = ["route", "sequence"]
    query_param_filters = {"route": "route_id", "checkpoint": "checkpoint_id"}


class PatrolRoundViewSet(StaffGuardingViewSet):
    queryset = PatrolRound.objects.select_related("route", "route__post", "assignment", "assignment__guard")
    serializer_class = PatrolRoundSerializer
    search_fields = ["route__name", "route__post__name", "assignment__guard__first_name", "assignment__guard__last_name"]
    ordering_fields = ["scheduled_start", "scheduled_end", "started_at", "completed_at", "status", "created_at"]
    ordering = ["-scheduled_start"]
    query_param_filters = {"route": "route_id", "post": "route__post_id", "site": "route__post__site_id", "assignment": "assignment_id", "status": "status"}

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        patrol_round = complete_patrol_round(self.get_object())
        return Response(self.get_serializer(patrol_round).data)


class CheckpointScanViewSet(StaffGuardingViewSet):
    queryset = CheckpointScan.objects.select_related("patrol_round", "checkpoint", "guard")
    serializer_class = CheckpointScanSerializer
    search_fields = ["checkpoint__name", "checkpoint__code", "guard__first_name", "guard__last_name", "guard__employee_number"]
    ordering_fields = ["scanned_at", "created_at", "within_geofence"]
    ordering = ["-scanned_at"]
    query_param_filters = {"patrol_round": "patrol_round_id", "checkpoint": "checkpoint_id", "guard": "guard_id", "within_geofence": "within_geofence"}


class FieldReportViewSet(StaffGuardingViewSet):
    queryset = FieldReport.objects.select_related("site", "post", "assignment", "guard", "reviewed_by").prefetch_related("attachments")
    serializer_class = FieldReportSerializer
    search_fields = ["title", "body", "site__name", "post__name", "guard__first_name", "guard__last_name", "guard__employee_number"]
    ordering_fields = ["submitted_at", "created_at", "status", "report_type", "visible_to_client"]
    ordering = ["-submitted_at"]
    query_param_filters = {"site": "site_id", "post": "post_id", "guard": "guard_id", "assignment": "assignment_id", "status": "status", "report_type": "report_type", "visible_to_client": "visible_to_client"}

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        class ReportReviewSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=[FieldReport.Status.APPROVED, FieldReport.Status.REJECTED])
            note = serializers.CharField(required=False, allow_blank=True)

        serializer = ReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = review_field_report(
            self.get_object(),
            actor=request.user,
            status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(self.get_serializer(report).data)


class GuardLocationPingViewSet(StaffGuardingViewSet):
    queryset = GuardLocationPing.objects.select_related("guard", "assignment")
    serializer_class = GuardLocationPingSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name"]
    ordering_fields = ["created_at", "device_timestamp"]
    ordering = ["-created_at"]
    query_param_filters = {"guard": "guard_id", "assignment": "assignment_id"}


class WelfareCheckViewSet(StaffGuardingViewSet):
    queryset = WelfareCheck.objects.select_related("assignment", "assignment__guard")
    serializer_class = WelfareCheckSerializer
    search_fields = ["assignment__guard__employee_number", "assignment__guard__first_name", "assignment__guard__last_name"]
    ordering_fields = ["due_at", "responded_at", "status", "created_at"]
    ordering = ["due_at"]
    query_param_filters = {"assignment": "assignment_id", "status": "status"}

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        check = respond_to_welfare_check(self.get_object(), note=request.data.get("note", ""))
        return Response(self.get_serializer(check).data)


class GuardPanicAlertViewSet(StaffGuardingViewSet):
    queryset = GuardPanicAlert.objects.select_related("guard", "assignment", "site", "acknowledged_by", "resolved_by")
    serializer_class = GuardPanicAlertSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name", "site__name", "note"]
    ordering_fields = ["created_at", "acknowledged_at", "resolved_at", "status"]
    ordering = ["-created_at"]
    query_param_filters = {"guard": "guard_id", "site": "site_id", "assignment": "assignment_id", "status": "status"}

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = acknowledge_panic_alert(self.get_object(), actor=request.user)
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = resolve_panic_alert(self.get_object(), actor=request.user)
        return Response(self.get_serializer(alert).data)


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
    search_fields = ["title", "description", "site__name", "assigned_guard__first_name", "assigned_guard__last_name", "assigned_guard__employee_number"]
    ordering_fields = ["created_at", "updated_at", "status", "priority", "assigned_at", "arrived_at", "resolved_at"]
    ordering = ["-created_at"]
    query_param_filters = {"site": "site_id", "assigned_guard": "assigned_guard_id", "status": "status", "priority": "priority", "alarm_event": "alarm_event_id", "emergency_request": "emergency_request_id", "panic_alert": "panic_alert_id"}

    def perform_create(self, serializer):
        assigned_guard = serializer.validated_data.get("assigned_guard")
        serializer.save(
            created_by=self.request.user,
            status=DispatchTask.Status.ASSIGNED if assigned_guard else DispatchTask.Status.OPEN,
            assigned_at=timezone.now() if assigned_guard else None,
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        class DispatchTransitionSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=DispatchTask.Status.choices)
            note = serializers.CharField(required=False, allow_blank=True)

        serializer = DispatchTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = transition_dispatch_task(
            self.get_object(),
            status=serializer.validated_data["status"],
            actor=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(self.get_serializer(task).data)


class MyShiftAssignmentListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShiftAssignmentSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard").filter(
            guard=guard
        )


class MyShiftAssignmentActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    allowed_actions = {"accept", "decline"}

    @extend_schema(
        request=inline_serializer(
            name="GuardAssignmentActionRequest",
            fields={"note": serializers.CharField(required=False, allow_blank=True)},
        ),
        responses=ShiftAssignmentSerializer,
    )
    def post(self, request, assignment_id, action):
        if action not in self.allowed_actions:
            raise ValidationError({"action": "Unsupported assignment action."})
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        if action == "accept":
            assignment = accept_assignment(assignment)
        else:
            assignment = decline_assignment(assignment, note=request.data.get("note", ""))
        return Response(ShiftAssignmentSerializer(assignment).data)


class MyClockEventCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ClockEventSerializer, responses=ClockEventSerializer)
    def post(self, request, assignment_id):
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        serializer = ClockEventSerializer(data={**request.data, "assignment": assignment.id})
        serializer.is_valid(raise_exception=True)
        clock_event = serializer.save()
        return Response(ClockEventSerializer(clock_event).data, status=status.HTTP_201_CREATED)


class MyCheckpointScanCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CheckpointScanSerializer, responses=CheckpointScanSerializer)
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
            transition_patrol_round(patrol_round, PatrolRound.Status.IN_PROGRESS)
        return Response(CheckpointScanSerializer(scan).data, status=status.HTTP_201_CREATED)


class MyPatrolRoundCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=PatrolRoundSerializer)
    def post(self, request, patrol_round_id):
        guard = get_guard_for_user(request.user)
        patrol_round = get_object_or_404(
            PatrolRound.objects.select_related("assignment"),
            id=patrol_round_id,
            assignment__guard=guard,
        )
        patrol_round = complete_patrol_round(patrol_round)
        return Response(PatrolRoundSerializer(patrol_round).data)


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

    @extend_schema(request=GuardLocationPingSerializer, responses=GuardLocationPingSerializer)
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

    @extend_schema(request=GuardPanicAlertSerializer, responses=GuardPanicAlertSerializer)
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


class MyWelfareCheckConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            name="GuardWelfareConfirmRequest",
            fields={"note": serializers.CharField(required=False, allow_blank=True)},
        ),
        responses=WelfareCheckSerializer,
    )
    def post(self, request, welfare_check_id):
        guard = get_guard_for_user(request.user)
        check = get_object_or_404(WelfareCheck, id=welfare_check_id, assignment__guard=guard)
        check = respond_to_welfare_check(check, note=request.data.get("note", ""))
        return Response(WelfareCheckSerializer(check).data)


class MyDispatchTaskListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DispatchTaskSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return DispatchTask.objects.select_related("site", "assigned_guard").filter(assigned_guard=guard)


class MyDispatchTaskTransitionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    allowed_actions = {
        "accept": DispatchTask.Status.ACCEPTED,
        "en-route": DispatchTask.Status.EN_ROUTE,
        "arrive": DispatchTask.Status.ARRIVED,
        "resolve": DispatchTask.Status.RESOLVED,
    }

    @extend_schema(
        request=inline_serializer(
            name="GuardDispatchTransitionRequest",
            fields={"note": serializers.CharField(required=False, allow_blank=True)},
        ),
        responses=DispatchTaskSerializer,
    )
    def post(self, request, task_id, action):
        if action not in self.allowed_actions:
            raise ValidationError({"action": "Unsupported dispatch action."})
        guard = get_guard_for_user(request.user)
        task = get_object_or_404(DispatchTask, id=task_id, assigned_guard=guard)
        task = transition_dispatch_task(
            task,
            status=self.allowed_actions[action],
            actor=request.user,
            note=request.data.get("note", ""),
        )
        return Response(DispatchTaskSerializer(task).data)
