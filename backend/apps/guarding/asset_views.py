from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .asset_models import (
    GuardAssetDepot,
    GuardAssetMaintenanceLog,
    GuardAssetStock,
    GuardAssetType,
    GuardAssetUnit,
    GuardingAssetPolicy,
    PostAssetKit,
    PostAssetKitLine,
    ShiftAssetManifest,
    ShiftAssetManifestLine,
)
from .asset_serializers import (
    AssetOverrideSerializer,
    GuardAssetDepotSerializer,
    GuardAssetMaintenanceLogSerializer,
    GuardAssetStockSerializer,
    GuardAssetTypeSerializer,
    GuardAssetUnitSerializer,
    GuardingAssetPolicySerializer,
    IssueManifestLineSerializer,
    PostAssetKitLineSerializer,
    PostAssetKitSerializer,
    ReturnManifestLineSerializer,
    ShiftAssetManifestLineSerializer,
    ShiftAssetManifestSerializer,
)
from .asset_services import (
    asset_readiness_for_assignment,
    build_manifest_for_assignment,
    close_manifest,
    guard_confirms_manifest,
    issue_manifest_line,
    override_asset_enforcement,
    return_manifest_line,
)
from .models import ShiftAssignment
from .views import StaffGuardingViewSet, get_guard_for_user


class GuardAssetTypeViewSet(StaffGuardingViewSet):
    queryset = GuardAssetType.objects.all()
    serializer_class = GuardAssetTypeSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code", "category", "created_at"]
    ordering = ["name"]
    query_param_filters = {"category": "category", "is_active": "is_active", "tracking_mode": "tracking_mode"}


class GuardAssetDepotViewSet(StaffGuardingViewSet):
    queryset = GuardAssetDepot.objects.select_related("site")
    serializer_class = GuardAssetDepotSerializer
    search_fields = ["name", "site__name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    query_param_filters = {"site": "site_id", "is_active": "is_active"}


class GuardAssetUnitViewSet(StaffGuardingViewSet):
    queryset = GuardAssetUnit.objects.select_related("asset_type", "depot", "site")
    serializer_class = GuardAssetUnitSerializer
    search_fields = ["asset_tag", "serial_number", "asset_type__name", "asset_type__code"]
    ordering_fields = ["asset_tag", "status", "created_at"]
    ordering = ["asset_tag"]
    query_param_filters = {
        "asset_type": "asset_type_id",
        "depot": "depot_id",
        "status": "status",
        "site": "site_id",
    }


class GuardAssetStockViewSet(StaffGuardingViewSet):
    queryset = GuardAssetStock.objects.select_related("asset_type", "depot")
    serializer_class = GuardAssetStockSerializer
    search_fields = ["asset_type__name", "asset_type__code", "depot__name"]
    ordering_fields = ["quantity_on_hand", "updated_at"]
    ordering = ["depot__name", "asset_type__name"]
    query_param_filters = {"asset_type": "asset_type_id", "depot": "depot_id"}


class GuardAssetMaintenanceLogViewSet(StaffGuardingViewSet):
    queryset = GuardAssetMaintenanceLog.objects.select_related("unit", "performed_by")
    serializer_class = GuardAssetMaintenanceLogSerializer
    ordering = ["-started_at"]
    query_param_filters = {"unit": "unit_id"}

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)


class GuardingAssetPolicyViewSet(StaffGuardingViewSet):
    queryset = GuardingAssetPolicy.objects.select_related("site", "post")
    serializer_class = GuardingAssetPolicySerializer
    query_param_filters = {"site": "site_id", "post": "post_id", "is_active": "is_active"}


class PostAssetKitViewSet(StaffGuardingViewSet):
    queryset = PostAssetKit.objects.select_related("post", "post__site").prefetch_related("lines__asset_type")
    serializer_class = PostAssetKitSerializer
    search_fields = ["name", "post__name", "post__site__name"]
    ordering = ["post__name", "name"]
    query_param_filters = {"post": "post_id", "is_active": "is_active"}


class PostAssetKitLineViewSet(StaffGuardingViewSet):
    queryset = PostAssetKitLine.objects.select_related("kit", "asset_type")
    serializer_class = PostAssetKitLineSerializer
    query_param_filters = {"kit": "kit_id"}


class ShiftAssetManifestViewSet(StaffGuardingViewSet):
    queryset = ShiftAssetManifest.objects.select_related(
        "assignment",
        "assignment__guard",
        "assignment__shift",
        "assignment__shift__post",
        "depot",
        "issued_by",
        "closed_by",
    ).prefetch_related("lines__asset_type", "lines__asset_unit")
    serializer_class = ShiftAssetManifestSerializer
    search_fields = [
        "assignment__guard__first_name",
        "assignment__guard__last_name",
        "assignment__shift__post__name",
    ]
    ordering_fields = ["created_at", "issued_at", "status"]
    ordering = ["-created_at"]
    query_param_filters = {
        "assignment": "assignment_id",
        "status": "status",
        "guard": "assignment__guard_id",
    }

    @extend_schema(request=IssueManifestLineSerializer, responses=ShiftAssetManifestLineSerializer)
    @action(detail=True, methods=["post"], url_path="issue-line")
    def issue_line(self, request, pk=None):
        manifest = self.get_object()
        payload = IssueManifestLineSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        line = get_object_or_404(
            ShiftAssetManifestLine,
            pk=payload.validated_data["line_id"],
            manifest=manifest,
        )
        depot = None
        if payload.validated_data.get("depot_id"):
            depot = get_object_or_404(GuardAssetDepot, pk=payload.validated_data["depot_id"])
        unit = None
        if payload.validated_data.get("asset_unit_id"):
            unit = get_object_or_404(GuardAssetUnit, pk=payload.validated_data["asset_unit_id"])
        line = issue_manifest_line(
            line,
            asset_unit=unit,
            quantity=payload.validated_data.get("quantity") or 1,
            condition_out=payload.validated_data.get("condition_out", ""),
            issued_by=request.user,
            depot=depot or manifest.depot,
        )
        return Response(ShiftAssetManifestLineSerializer(line).data)

    @extend_schema(request=ReturnManifestLineSerializer, responses=ShiftAssetManifestLineSerializer)
    @action(detail=True, methods=["post"], url_path="return-line")
    def return_line(self, request, pk=None):
        manifest = self.get_object()
        payload = ReturnManifestLineSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        line = get_object_or_404(
            ShiftAssetManifestLine,
            pk=payload.validated_data["line_id"],
            manifest=manifest,
        )
        line = return_manifest_line(
            line,
            quantity=payload.validated_data.get("quantity"),
            condition_in=payload.validated_data.get("condition_in", ""),
            status=payload.validated_data.get("status"),
            returned_by=request.user,
            notes=payload.validated_data.get("notes", ""),
        )
        return Response(ShiftAssetManifestLineSerializer(line).data)

    @extend_schema(request=None, responses=ShiftAssetManifestSerializer)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        manifest = close_manifest(self.get_object(), closed_by=request.user)
        return Response(self.get_serializer(manifest).data)

    @extend_schema(request=AssetOverrideSerializer, responses=ShiftAssetManifestSerializer)
    @action(detail=True, methods=["post"], url_path="override-enforcement")
    def override_enforcement(self, request, pk=None):
        manifest = self.get_object()
        payload = AssetOverrideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        manifest = override_asset_enforcement(
            manifest,
            phase=payload.validated_data["phase"],
            reason=payload.validated_data["reason"],
            actor=request.user,
        )
        return Response(self.get_serializer(manifest).data)


class ShiftAssetManifestLineViewSet(StaffGuardingViewSet):
    queryset = ShiftAssetManifestLine.objects.select_related("manifest", "asset_type", "asset_unit")
    serializer_class = ShiftAssetManifestLineSerializer
    query_param_filters = {"manifest": "manifest_id", "status": "status"}


class ShiftAssetManifestBuildView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(request=None, responses=ShiftAssetManifestSerializer)
    def post(self, request, assignment_id):
        assignment = get_object_or_404(
            ShiftAssignment.objects.select_related("shift__post"),
            pk=assignment_id,
        )
        depot = None
        depot_id = request.data.get("depot_id")
        if depot_id:
            depot = get_object_or_404(GuardAssetDepot, pk=depot_id)
        manifest = build_manifest_for_assignment(assignment, depot=depot, issued_by=request.user)
        return Response(ShiftAssetManifestSerializer(manifest).data, status=status.HTTP_201_CREATED)


class MyShiftAssetManifestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=ShiftAssetManifestSerializer)
    def get(self, request, assignment_id):
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        manifest = getattr(assignment, "asset_manifest", None)
        if manifest is None:
            raise ValidationError({"manifest": "No asset manifest for this shift."})
        return Response(ShiftAssetManifestSerializer(manifest).data)


class MyShiftAssetConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=ShiftAssetManifestSerializer)
    def post(self, request, assignment_id):
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        manifest = getattr(assignment, "asset_manifest", None)
        if manifest is None:
            raise ValidationError({"manifest": "No asset manifest for this shift."})
        manifest = guard_confirms_manifest(manifest)
        return Response(ShiftAssetManifestSerializer(manifest).data)


class MyShiftAssetReadinessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, assignment_id):
        guard = get_guard_for_user(request.user)
        assignment = get_object_or_404(ShiftAssignment, id=assignment_id, guard=guard)
        phase = request.query_params.get("phase", "clock_in")
        readiness = asset_readiness_for_assignment(assignment, phase=phase)
        return Response(
            {
                "ok": readiness.ok,
                "mode": readiness.mode,
                "blockers": readiness.blockers,
                "advisory_warnings": readiness.advisory_warnings,
            }
        )
