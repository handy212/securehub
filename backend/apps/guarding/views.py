from datetime import timedelta

from django.db import models
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasConsolePermission
from apps.accounts.rbac import Perm
from apps.sites.models import Site

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
    PatrolRound,
    PatrolRouteCheckpoint,
    PostOrder,
    ReportTemplate,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    ShiftTemplate,
    WelfareCheck,
)
from .serializers import (
    CheckpointScanSerializer,
    CheckpointSerializer,
    ClockEventSerializer,
    ClientPortalAccessSerializer,
    DispatchTaskSerializer,
    FieldReportAcknowledgementSerializer,
    FieldReportSerializer,
    GuardApplicantSerializer,
    GuardApplicantDocumentSerializer,
    GuardApplicantEducationSerializer,
    GuardApplicantEmploymentSerializer,
    GuardApplicantProfileSerializer,
    GuardApplicantReferenceSerializer,
    GuardAvailabilitySerializer,
    GuardContractSerializer,
    GuardCredentialSerializer,
    GuardDocumentSerializer,
    GuardEquipmentIssueSerializer,
    GuardInvoiceLineSerializer,
    GuardInvoiceSerializer,
    GuardOffboardingChecklistSerializer,
    GuardTimesheetSerializer,
    GuardTrainingRecordSerializer,
    GuardingEventLogSerializer,
    GuardLocationPingSerializer,
    GuardPanicAlertSerializer,
    GuardPostSerializer,
    GuardProfileSerializer,
    LeaveRequestSerializer,
    PatrolRouteSerializer,
    PatrolRoundMobileSerializer,
    PatrolRoundSerializer,
    PostOrderSerializer,
    ReportTemplateSerializer,
    ShiftAssignmentSerializer,
    ShiftSerializer,
    ShiftSwapRequestSerializer,
    WelfareCheckMobileSerializer,
    WelfareCheckSerializer,
    ShiftTemplateSerializer,
    PatrolRouteCheckpointSerializer,
)
from .services import (
    accept_assignment,
    acknowledge_field_report,
    acknowledge_panic_alert,
    assign_dispatch_task,
    build_checkpoint_scan_response,
    build_command_center_snapshot,
    complete_patrol_round,
    create_shift_swap_request,
    decline_assignment,
    generate_guard_invoice,
    guard_qualification_gaps,
    hire_applicant,
    mark_assignment_no_show,
    record_checkpoint_scan,
    respond_to_welfare_check,
    resolve_panic_alert,
    review_leave_request,
    review_shift_swap_request,
    review_timesheet,
    review_field_report,
    suggest_nearest_guards,
    transition_guard_invoice,
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
    permission_classes = [permissions.IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.MANAGE_GUARDING
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
    queryset = (
        GuardApplicant.objects.select_related("created_by", "hired_guard", "profile")
        .prefetch_related("documents", "education_records", "employment_records", "references")
    )
    serializer_class = GuardApplicantSerializer
    search_fields = ["first_name", "last_name", "email", "phone_number", "source", "national_id"]
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


class GuardApplicantDocumentViewSet(StaffGuardingViewSet):
    queryset = GuardApplicantDocument.objects.select_related("applicant", "uploaded_by")
    serializer_class = GuardApplicantDocumentSerializer
    search_fields = ["title", "reference_number"]
    ordering = ["-created_at"]
    query_param_filters = {"applicant": "applicant_id"}

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class GuardApplicantEducationViewSet(StaffGuardingViewSet):
    queryset = GuardApplicantEducation.objects.select_related("applicant")
    serializer_class = GuardApplicantEducationSerializer
    search_fields = ["education_level", "institution_name"]
    ordering = ["-year_completed"]
    query_param_filters = {"applicant": "applicant_id"}


class GuardApplicantEmploymentViewSet(StaffGuardingViewSet):
    queryset = GuardApplicantEmployment.objects.select_related("applicant")
    serializer_class = GuardApplicantEmploymentSerializer
    search_fields = ["company_name", "position"]
    ordering = ["-started_on"]
    query_param_filters = {"applicant": "applicant_id"}


class GuardApplicantReferenceViewSet(StaffGuardingViewSet):
    queryset = GuardApplicantReference.objects.select_related("applicant")
    serializer_class = GuardApplicantReferenceSerializer
    search_fields = ["full_name", "company", "phone_number"]
    ordering = ["full_name"]
    query_param_filters = {"applicant": "applicant_id"}


class GuardApplicantProfileViewSet(StaffGuardingViewSet):
    queryset = GuardApplicantProfile.objects.select_related("applicant")
    serializer_class = GuardApplicantProfileSerializer
    ordering = ["-updated_at"]
    query_param_filters = {"applicant": "applicant_id"}


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

    @action(detail=True, methods=["get"])
    def qualification(self, request, pk=None):
        guard = self.get_object()
        post = get_object_or_404(GuardPost, pk=request.query_params.get("post"))
        gaps = guard_qualification_gaps(guard, post)
        return Response(
            {
                "guard": str(guard.id),
                "post": str(post.id),
                "qualified": not gaps,
                "missing": gaps,
            }
        )


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


class GuardTrainingRecordViewSet(StaffGuardingViewSet):
    queryset = GuardTrainingRecord.objects.select_related("guard")
    serializer_class = GuardTrainingRecordSerializer
    search_fields = ["name", "provider", "certificate_number", "guard__first_name", "guard__last_name"]
    ordering_fields = ["expires_on", "completed_on", "status", "name", "created_at"]
    ordering = ["expires_on", "name"]
    query_param_filters = {"guard": "guard_id", "status": "status"}


class GuardEquipmentIssueViewSet(StaffGuardingViewSet):
    queryset = GuardEquipmentIssue.objects.select_related("guard", "issued_by")
    serializer_class = GuardEquipmentIssueSerializer
    search_fields = ["item_name", "item_code", "guard__first_name", "guard__last_name", "guard__employee_number"]
    ordering_fields = ["issued_at", "returned_at", "status", "item_name"]
    ordering = ["-issued_at"]
    query_param_filters = {"guard": "guard_id", "status": "status"}

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


class GuardOffboardingChecklistViewSet(StaffGuardingViewSet):
    queryset = GuardOffboardingChecklist.objects.select_related("guard", "completed_by")
    serializer_class = GuardOffboardingChecklistSerializer
    search_fields = ["guard__first_name", "guard__last_name", "guard__employee_number", "exit_notes"]
    ordering_fields = ["created_at", "updated_at", "completed_at"]
    ordering = ["-created_at"]
    query_param_filters = {"guard": "guard_id"}

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        checklist = self.get_object()
        checklist.equipment_returned = True
        checklist.documents_archived = True
        checklist.access_revoked = True
        checklist.final_timesheet_approved = True
        checklist.completed_by = request.user
        checklist.completed_at = timezone.now()
        checklist.save(
            update_fields=[
                "equipment_returned",
                "documents_archived",
                "access_revoked",
                "final_timesheet_approved",
                "completed_by",
                "completed_at",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(checklist).data)


class GuardPostViewSet(StaffGuardingViewSet):
    queryset = GuardPost.objects.select_related("site", "supervisor")
    serializer_class = GuardPostSerializer
    search_fields = ["name", "code", "site__name", "description"]
    ordering_fields = ["name", "site__name", "created_at", "is_active"]
    ordering = ["site__name", "name"]
    query_param_filters = {"site": "site_id", "is_active": "is_active", "supervisor": "supervisor_id"}


class GuardContractViewSet(StaffGuardingViewSet):
    queryset = GuardContract.objects.select_related("site", "post")
    serializer_class = GuardContractSerializer
    search_fields = ["name", "site__name", "post__name", "notes"]
    ordering_fields = ["starts_on", "ends_on", "status", "bill_rate", "pay_rate", "created_at"]
    ordering = ["site__name", "name"]
    query_param_filters = {"site": "site_id", "post": "post_id", "status": "status"}


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


class ShiftSwapRequestViewSet(StaffGuardingViewSet):
    queryset = ShiftSwapRequest.objects.select_related(
        "assignment",
        "assignment__shift",
        "assignment__shift__post",
        "assignment__shift__post__site",
        "requested_by",
        "target_guard",
        "reviewed_by",
    )
    serializer_class = ShiftSwapRequestSerializer
    search_fields = [
        "requested_by__employee_number",
        "requested_by__first_name",
        "requested_by__last_name",
        "target_guard__employee_number",
        "target_guard__first_name",
        "target_guard__last_name",
        "assignment__shift__post__name",
    ]
    ordering_fields = ["created_at", "reviewed_at", "status"]
    ordering = ["-created_at"]
    query_param_filters = {"status": "status", "requested_by": "requested_by_id", "target_guard": "target_guard_id"}

    def perform_create(self, serializer):
        assignment = serializer.validated_data["assignment"]
        swap = create_shift_swap_request(
            assignment,
            requested_by=assignment.guard,
            target_guard=serializer.validated_data.get("target_guard"),
            reason=serializer.validated_data.get("reason", ""),
        )
        serializer.instance = swap

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        class SwapReviewSerializer(serializers.Serializer):
            status = serializers.ChoiceField(
                choices=[
                    ShiftSwapRequest.Status.APPROVED,
                    ShiftSwapRequest.Status.REJECTED,
                    ShiftSwapRequest.Status.CANCELLED,
                ]
            )
            note = serializers.CharField(required=False, allow_blank=True)

        serializer = SwapReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        swap = review_shift_swap_request(
            self.get_object(),
            actor=request.user,
            status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(self.get_serializer(swap).data)


class GuardAvailabilityViewSet(StaffGuardingViewSet):
    queryset = GuardAvailability.objects.select_related("guard", "created_by")
    serializer_class = GuardAvailabilitySerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name", "reason"]
    ordering_fields = ["starts_at", "ends_at", "availability_type", "created_at"]
    ordering = ["starts_at"]
    query_param_filters = {"guard": "guard_id", "availability_type": "availability_type"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class LeaveRequestViewSet(StaffGuardingViewSet):
    queryset = LeaveRequest.objects.select_related("guard", "reviewed_by")
    serializer_class = LeaveRequestSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name", "reason", "review_note"]
    ordering_fields = ["starts_at", "ends_at", "status", "created_at"]
    ordering = ["-starts_at"]
    query_param_filters = {"guard": "guard_id", "status": "status"}

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        class LeaveReviewSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=[LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED])
            note = serializers.CharField(required=False, allow_blank=True)

        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = review_leave_request(
            self.get_object(),
            actor=request.user,
            status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(self.get_serializer(leave_request).data)


class ShiftTemplateViewSet(StaffGuardingViewSet):
    queryset = ShiftTemplate.objects.select_related("post", "post__site")
    serializer_class = ShiftTemplateSerializer
    search_fields = ["name", "post__name", "post__site__name", "notes"]
    ordering_fields = ["name", "start_time", "end_time", "required_guards", "is_active"]
    ordering = ["post", "name"]
    query_param_filters = {"post": "post_id", "site": "post__site_id", "is_active": "is_active"}


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
    queryset = FieldReport.objects.select_related("site", "post", "assignment", "guard", "reviewed_by").prefetch_related("attachments", "client_acknowledgements")
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


class FieldReportAcknowledgementViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.VIEW_GUARDING
    serializer_class = FieldReportAcknowledgementSerializer
    queryset = FieldReportAcknowledgement.objects.select_related("report", "report__site", "user")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["report__title", "report__site__name", "user__username", "comment"]
    ordering_fields = ["acknowledged_at"]
    ordering = ["-acknowledged_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        for param, field_name in {"report": "report_id", "user": "user_id", "site": "report__site_id"}.items():
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                queryset = queryset.filter(**{field_name: value})
        return queryset


class ReportTemplateViewSet(StaffGuardingViewSet):
    queryset = ReportTemplate.objects.select_related("site", "created_by")
    serializer_class = ReportTemplateSerializer
    search_fields = ["name", "site__name"]
    ordering_fields = ["name", "report_type", "is_active", "created_at"]
    ordering = ["report_type", "name"]
    query_param_filters = {"site": "site_id", "report_type": "report_type", "is_active": "is_active"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GuardLocationPingViewSet(StaffGuardingViewSet):
    queryset = GuardLocationPing.objects.select_related("guard", "assignment")
    serializer_class = GuardLocationPingSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name"]
    ordering_fields = ["created_at", "device_timestamp"]
    ordering = ["-created_at"]
    query_param_filters = {"guard": "guard_id", "assignment": "assignment_id"}


class GuardTimesheetViewSet(StaffGuardingViewSet):
    queryset = GuardTimesheet.objects.select_related("assignment", "guard", "site", "post", "approved_by")
    serializer_class = GuardTimesheetSerializer
    search_fields = ["guard__employee_number", "guard__first_name", "guard__last_name", "site__name", "post__name"]
    ordering_fields = ["period_start", "period_end", "status", "regular_minutes", "overtime_minutes", "pay_amount", "bill_amount"]
    ordering = ["-period_start"]
    query_param_filters = {"guard": "guard_id", "site": "site_id", "post": "post_id", "status": "status"}

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        class TimesheetReviewSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=GuardTimesheet.Status.choices)
            note = serializers.CharField(required=False, allow_blank=True)

        serializer = TimesheetReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        timesheet = review_timesheet(
            self.get_object(),
            actor=request.user,
            status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(self.get_serializer(timesheet).data)


class GuardInvoiceViewSet(StaffGuardingViewSet):
    queryset = GuardInvoice.objects.select_related("site", "contract", "generated_by").prefetch_related("lines", "lines__timesheet")
    serializer_class = GuardInvoiceSerializer
    search_fields = ["invoice_number", "site__name", "contract__name", "notes"]
    ordering_fields = ["period_start", "period_end", "status", "subtotal", "total", "created_at"]
    ordering = ["-period_start", "-created_at"]
    query_param_filters = {"site": "site_id", "contract": "contract_id", "status": "status"}

    @action(detail=False, methods=["post"])
    def generate(self, request):
        class InvoiceGenerateSerializer(serializers.Serializer):
            site = serializers.UUIDField()
            contract = serializers.UUIDField(required=False)
            period_start = serializers.DateField()
            period_end = serializers.DateField()

        serializer = InvoiceGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        site = get_object_or_404(Site, pk=serializer.validated_data["site"])
        contract = None
        if serializer.validated_data.get("contract"):
            contract = get_object_or_404(GuardContract, pk=serializer.validated_data["contract"], site=site)
        invoice = generate_guard_invoice(
            site=site,
            contract=contract,
            period_start=serializer.validated_data["period_start"],
            period_end=serializer.validated_data["period_end"],
            actor=request.user,
        )
        return Response(self.get_serializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        class InvoiceTransitionSerializer(serializers.Serializer):
            status = serializers.ChoiceField(choices=GuardInvoice.Status.choices)

        serializer = InvoiceTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = transition_guard_invoice(
            self.get_object(),
            status=serializer.validated_data["status"],
            actor=request.user,
        )
        return Response(self.get_serializer(invoice).data)


class GuardInvoiceLineViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.MANAGE_GUARDING
    serializer_class = GuardInvoiceLineSerializer
    queryset = GuardInvoiceLine.objects.select_related("invoice", "timesheet", "timesheet__guard")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice__invoice_number", "description", "timesheet__guard__first_name", "timesheet__guard__last_name"]
    ordering_fields = ["created_at", "amount", "quantity_hours"]
    ordering = ["created_at"]


class ClientPortalAccessViewSet(StaffGuardingViewSet):
    queryset = ClientPortalAccess.objects.select_related("user", "site")
    serializer_class = ClientPortalAccessSerializer
    search_fields = ["user__username", "user__email", "site__name"]
    ordering_fields = ["created_at", "role", "site__name", "user__username"]
    ordering = ["site__name", "user__username"]
    query_param_filters = {"user": "user_id", "site": "site_id", "role": "role"}


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


class CommandCenterSnapshotView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.VIEW_GUARDING

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(build_command_center_snapshot())


class DispatchSuggestGuardsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.MANAGE_GUARDING

    @extend_schema(responses={200: list})
    def get(self, request, task_id):
        task = get_object_or_404(DispatchTask.objects.select_related("site"), id=task_id)
        if task.target_latitude is None or task.target_longitude is None:
            return Response([])
        suggestions = suggest_nearest_guards(
            task.site,
            float(task.target_latitude),
            float(task.target_longitude),
            limit=int(request.query_params.get("limit", 5)),
        )
        return Response(
            [
                {
                    "guard_id": str(item["guard"].id),
                    "guard_name": item["guard"].full_name,
                    "distance_km": item["distance_km"],
                    "assignment_id": str(item["assignment"].id),
                }
                for item in suggestions
            ]
        )


class PatrolRoundPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, patrol_round_id):
        patrol_round = get_object_or_404(
            PatrolRound.objects.select_related(
                "route",
                "route__post",
                "route__post__site",
                "assignment",
                "assignment__guard",
            ).prefetch_related("scans__checkpoint"),
            id=patrol_round_id,
        )
        if not request.user.is_staff:
            guard = get_guard_for_user(request.user)
            if patrol_round.assignment_id is None or patrol_round.assignment.guard_id != guard.id:
                raise PermissionDenied("You cannot access this patrol report.")
        from django.http import HttpResponse

        from .reports.pdf import render_patrol_round_pdf

        pdf_bytes = render_patrol_round_pdf(patrol_round)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="patrol-{patrol_round_id}.pdf"'
        return response


class MyPatrolRoundListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PatrolRoundMobileSerializer
    http_method_names = ["get"]
    pagination_class = None

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return (
            PatrolRound.objects.select_related("route", "route__post", "route__post__site", "assignment")
            .prefetch_related("route__patrolroutecheckpoint_set__checkpoint", "scans__checkpoint")
            .filter(assignment__guard=guard)
            .order_by("-scheduled_start")
        )


class MyShiftAssignmentListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShiftAssignmentSerializer
    http_method_names = ["get"]
    pagination_class = None

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard").filter(
            guard=guard
        )


class MyPostOrderListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostOrderSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        post_ids = ShiftAssignment.objects.filter(guard=guard).values_list("shift__post_id", flat=True)
        return PostOrder.objects.select_related("post", "post__site").filter(post_id__in=post_ids, is_active=True)


class MyReportTemplateListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportTemplateSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        site_ids = ShiftAssignment.objects.filter(guard=guard).values_list("shift__post__site_id", flat=True)
        return ReportTemplate.objects.select_related("site").filter(is_active=True).filter(
            models.Q(site__isnull=True) | models.Q(site_id__in=site_ids)
        )


class MyAvailabilityListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardAvailabilitySerializer

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return GuardAvailability.objects.filter(guard=guard).order_by("starts_at")

    def perform_create(self, serializer):
        guard = get_guard_for_user(self.request.user)
        serializer.save(guard=guard, created_by=self.request.user)


class MyLeaveRequestListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return LeaveRequest.objects.filter(guard=guard).order_by("-starts_at")

    def perform_create(self, serializer):
        guard = get_guard_for_user(self.request.user)
        serializer.save(guard=guard)


class MyShiftSwapRequestListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShiftSwapRequestSerializer

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return (
            ShiftSwapRequest.objects.select_related(
                "assignment",
                "assignment__shift",
                "assignment__shift__post",
                "assignment__shift__post__site",
                "requested_by",
                "target_guard",
                "reviewed_by",
            )
            .filter(models.Q(requested_by=guard) | models.Q(target_guard=guard))
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        guard = get_guard_for_user(self.request.user)
        swap = create_shift_swap_request(
            serializer.validated_data["assignment"],
            requested_by=guard,
            target_guard=serializer.validated_data.get("target_guard"),
            reason=serializer.validated_data.get("reason", ""),
        )
        serializer.instance = swap


class MyTimesheetListView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardTimesheetSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        return GuardTimesheet.objects.select_related("assignment", "site", "post").filter(guard=guard)


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
        scan = record_checkpoint_scan(
            patrol_round=patrol_round,
            checkpoint=checkpoint,
            guard=guard,
            latitude=serializer.validated_data.get("latitude"),
            longitude=serializer.validated_data.get("longitude"),
            accuracy_m=serializer.validated_data.get("accuracy_m"),
            within_geofence=serializer.validated_data.get("within_geofence", False),
            offline_created_at=serializer.validated_data.get("offline_created_at"),
            client_scan_id=str(request.data.get("client_scan_id", "") or ""),
            metadata=serializer.validated_data.get("metadata"),
        )
        if patrol_round.status == PatrolRound.Status.SCHEDULED:
            transition_patrol_round(patrol_round, PatrolRound.Status.IN_PROGRESS)
        payload = CheckpointScanSerializer(scan).data
        payload.update(build_checkpoint_scan_response(scan))
        return Response(payload, status=status.HTTP_201_CREATED)


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


class ClientFieldReportAcknowledgeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            name="ClientReportAcknowledgeRequest",
            fields={"comment": serializers.CharField(required=False, allow_blank=True)},
        ),
        responses=FieldReportAcknowledgementSerializer,
    )
    def post(self, request, report_id):
        report = get_object_or_404(FieldReport, id=report_id)
        acknowledgement = acknowledge_field_report(report, user=request.user, comment=request.data.get("comment", ""))
        return Response(FieldReportAcknowledgementSerializer(acknowledgement).data)


class ClientPortalSnapshotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        access_records = list(ClientPortalAccess.objects.select_related("site").filter(user=request.user))
        if not access_records:
            raise PermissionDenied("Your account does not have guarding client portal access.")

        site_ids = [access.site_id for access in access_records]
        report_site_ids = [access.site_id for access in access_records if access.can_view_reports]
        acknowledge_site_ids = {access.site_id for access in access_records if access.can_acknowledge_reports}
        patrol_site_ids = [access.site_id for access in access_records if access.can_view_patrols]
        attendance_site_ids = [access.site_id for access in access_records if access.can_view_attendance]
        guard_site_ids = [access.site_id for access in access_records if access.can_view_guards]
        today = timezone.localdate()
        guard_window_end = today + timedelta(days=7)

        reports = (
            FieldReport.objects.select_related("site", "post", "guard")
            .prefetch_related("client_acknowledgements")
            .filter(site_id__in=report_site_ids, visible_to_client=True, status=FieldReport.Status.APPROVED)
            .order_by("-submitted_at")[:100]
        )
        patrol_rounds = (
            PatrolRound.objects.select_related("route", "route__post", "route__post__site", "assignment", "assignment__guard")
            .prefetch_related("scans")
            .filter(route__post__site_id__in=patrol_site_ids)
            .order_by("-scheduled_start")[:100]
        )
        assignments = (
            ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
            .filter(shift__post__site_id__in=attendance_site_ids)
            .order_by("-shift__starts_at")[:100]
        )
        known_guards = list(
            ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
            .prefetch_related(
                Prefetch(
                    "guard__credentials",
                    queryset=GuardCredential.objects.filter(verified=True).order_by("credential_type", "name"),
                    to_attr="verified_client_credentials",
                )
            )
            .filter(
                shift__post__site_id__in=guard_site_ids,
                shift__starts_at__date__gte=today,
                shift__starts_at__date__lte=guard_window_end,
                status__in=[
                    ShiftAssignment.Status.ASSIGNED,
                    ShiftAssignment.Status.ACCEPTED,
                    ShiftAssignment.Status.CLOCKED_IN,
                ],
            )
            .order_by("shift__starts_at", "shift__post__site__name", "shift__post__name", "guard__last_name")[:100]
        )

        return Response(
            {
                "counts": {
                    "sites": len(site_ids),
                    "reports": len(reports),
                    "patrols": len(patrol_rounds),
                    "assignments": len(assignments),
                    "guards": len({assignment.guard_id for assignment in known_guards}),
                },
                "access": [
                    {
                        "site_id": str(access.site_id),
                        "site_name": access.site.name,
                        "role": access.role,
                        "can_view_reports": access.can_view_reports,
                        "can_view_patrols": access.can_view_patrols,
                        "can_view_attendance": access.can_view_attendance,
                        "can_view_guards": access.can_view_guards,
                        "can_acknowledge_reports": access.can_acknowledge_reports,
                    }
                    for access in access_records
                ],
                "reports": [
                    {
                        "id": str(report.id),
                        "title": report.title,
                        "report_type": report.get_report_type_display(),
                        "body": report.body,
                        "site_name": report.site.name,
                        "post_name": report.post.name if report.post else "",
                        "guard_name": report.guard.full_name if report.guard else "",
                        "submitted_at": report.submitted_at,
                        "acknowledgement_count": report.client_acknowledgements.count(),
                        "can_acknowledge": report.site_id in acknowledge_site_ids,
                    }
                    for report in reports
                ],
                "patrol_rounds": [
                    {
                        "id": str(patrol.id),
                        "route_name": patrol.route.name,
                        "site_name": patrol.route.post.site.name,
                        "post_name": patrol.route.post.name,
                        "guard_name": patrol.assignment.guard.full_name if patrol.assignment and patrol.assignment.guard else "",
                        "status": patrol.get_status_display(),
                        "scan_count": patrol.scans.count(),
                        "scheduled_start": patrol.scheduled_start,
                    }
                    for patrol in patrol_rounds
                ],
                "assignments": [
                    {
                        "id": str(assignment.id),
                        "guard_name": assignment.guard.full_name,
                        "site_name": assignment.shift.post.site.name,
                        "post_name": assignment.shift.post.name,
                        "status": assignment.get_status_display(),
                        "starts_at": assignment.shift.starts_at,
                        "ends_at": assignment.shift.ends_at,
                    }
                    for assignment in assignments
                ],
                "known_guards": [
                    {
                        "assignment_id": str(assignment.id),
                        "guard_name": assignment.guard.full_name,
                        "employee_number": assignment.guard.employee_number,
                        "guard_status": assignment.guard.get_status_display(),
                        "site_name": assignment.shift.post.site.name,
                        "post_name": assignment.shift.post.name,
                        "starts_at": assignment.shift.starts_at,
                        "ends_at": assignment.shift.ends_at,
                        "assignment_status": assignment.get_status_display(),
                        "verified_credentials": [
                            credential.name
                            for credential in getattr(assignment.guard, "verified_client_credentials", [])
                        ],
                    }
                    for assignment in known_guards
                ],
            }
        )


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
        if assignment is None:
            assignment = (
                ShiftAssignment.objects.filter(guard=guard, status=ShiftAssignment.Status.CLOCKED_IN)
                .order_by("-clocked_in_at")
                .first()
            )
        if assignment is None or assignment.status != ShiftAssignment.Status.CLOCKED_IN:
            raise ValidationError({"assignment": "Location pings require an active clocked-in shift."})
        ping = serializer.save(guard=guard, assignment=assignment)
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


class MyWelfareCheckListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WelfareCheckMobileSerializer
    pagination_class = None

    @extend_schema(responses=WelfareCheckMobileSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        guard = get_guard_for_user(self.request.user)
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        return (
            WelfareCheck.objects.select_related(
                "assignment",
                "assignment__shift",
                "assignment__shift__post",
                "assignment__shift__post__site",
            )
            .filter(assignment__guard=guard)
            .filter(
                models.Q(status=WelfareCheck.Status.PENDING)
                | models.Q(
                    status=WelfareCheck.Status.MISSED,
                    due_at__gte=cutoff,
                )
            )
            .order_by("due_at")
        )


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
