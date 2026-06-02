from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import asset_views, views


router = DefaultRouter()
router.register("applicants", views.GuardApplicantViewSet, basename="guard-applicant")
router.register("applicant-documents", views.GuardApplicantDocumentViewSet, basename="guard-applicant-document")
router.register("applicant-education", views.GuardApplicantEducationViewSet, basename="guard-applicant-education")
router.register("applicant-employment", views.GuardApplicantEmploymentViewSet, basename="guard-applicant-employment")
router.register("applicant-references", views.GuardApplicantReferenceViewSet, basename="guard-applicant-reference")
router.register("applicant-profiles", views.GuardApplicantProfileViewSet, basename="guard-applicant-profile")
router.register("workflow-events", views.GuardingEventLogViewSet, basename="guarding-workflow-event")
router.register("guards", views.GuardProfileViewSet, basename="guard-profile")
router.register("credentials", views.GuardCredentialViewSet, basename="guard-credential")
router.register("documents", views.GuardDocumentViewSet, basename="guard-document")
router.register("training-records", views.GuardTrainingRecordViewSet, basename="guard-training-record")
router.register("equipment-issues", views.GuardEquipmentIssueViewSet, basename="guard-equipment-issue")
router.register("offboarding-checklists", views.GuardOffboardingChecklistViewSet, basename="guard-offboarding-checklist")
router.register("posts", views.GuardPostViewSet, basename="guard-post")
router.register("contracts", views.GuardContractViewSet, basename="guard-contract")
router.register("post-orders", views.PostOrderViewSet, basename="post-order")
router.register("availability", views.GuardAvailabilityViewSet, basename="guard-availability")
router.register("leave-requests", views.LeaveRequestViewSet, basename="guard-leave-request")
router.register("shift-templates", views.ShiftTemplateViewSet, basename="guard-shift-template")
router.register("shifts", views.ShiftViewSet, basename="guard-shift")
router.register("assignments", views.ShiftAssignmentViewSet, basename="guard-shift-assignment")
router.register("shift-swaps", views.ShiftSwapRequestViewSet, basename="guard-shift-swap")
router.register("clock-events", views.ClockEventViewSet, basename="guard-clock-event")
router.register("checkpoints", views.CheckpointViewSet, basename="guard-checkpoint")
router.register("patrol-routes", views.PatrolRouteViewSet, basename="guard-patrol-route")
router.register("patrol-route-checkpoints", views.PatrolRouteCheckpointViewSet, basename="guard-patrol-route-checkpoint")
router.register("patrol-rounds", views.PatrolRoundViewSet, basename="guard-patrol-round")
router.register("checkpoint-scans", views.CheckpointScanViewSet, basename="guard-checkpoint-scan")
router.register("report-templates", views.ReportTemplateViewSet, basename="guard-report-template")
router.register("reports", views.FieldReportViewSet, basename="guard-field-report")
router.register("report-acknowledgements", views.FieldReportAcknowledgementViewSet, basename="guard-report-acknowledgement")
router.register("location-pings", views.GuardLocationPingViewSet, basename="guard-location-ping")
router.register("timesheets", views.GuardTimesheetViewSet, basename="guard-timesheet")
router.register("invoices", views.GuardInvoiceViewSet, basename="guard-invoice")
router.register("invoice-lines", views.GuardInvoiceLineViewSet, basename="guard-invoice-line")
router.register("client-access", views.ClientPortalAccessViewSet, basename="guard-client-access")
router.register("welfare-checks", views.WelfareCheckViewSet, basename="guard-welfare-check")
router.register("panic-alerts", views.GuardPanicAlertViewSet, basename="guard-panic-alert")
router.register("dispatch-tasks", views.DispatchTaskViewSet, basename="guard-dispatch-task")
router.register("asset-types", asset_views.GuardAssetTypeViewSet, basename="guard-asset-type")
router.register("asset-depots", asset_views.GuardAssetDepotViewSet, basename="guard-asset-depot")
router.register("asset-units", asset_views.GuardAssetUnitViewSet, basename="guard-asset-unit")
router.register("asset-stock", asset_views.GuardAssetStockViewSet, basename="guard-asset-stock")
router.register("asset-maintenance", asset_views.GuardAssetMaintenanceLogViewSet, basename="guard-asset-maintenance")
router.register("asset-policies", asset_views.GuardingAssetPolicyViewSet, basename="guard-asset-policy")
router.register("post-asset-kits", asset_views.PostAssetKitViewSet, basename="guard-post-asset-kit")
router.register("post-asset-kit-lines", asset_views.PostAssetKitLineViewSet, basename="guard-post-asset-kit-line")
router.register("shift-asset-manifests", asset_views.ShiftAssetManifestViewSet, basename="guard-shift-asset-manifest")
router.register("shift-asset-manifest-lines", asset_views.ShiftAssetManifestLineViewSet, basename="guard-shift-asset-manifest-line")

urlpatterns = [
    path("", include(router.urls)),
    path("command-center/snapshot/", views.CommandCenterSnapshotView.as_view(), name="guard-command-center"),
    path("dispatch-tasks/<uuid:task_id>/suggest-guards/", views.DispatchSuggestGuardsView.as_view(), name="guard-dispatch-suggest"),
    path("patrol-rounds/<uuid:patrol_round_id>/pdf/", views.PatrolRoundPdfView.as_view(), name="guard-patrol-pdf"),
    path("me/patrol-rounds/", views.MyPatrolRoundListView.as_view(), name="guard-my-patrol-rounds"),
    path("me/shifts/", views.MyShiftAssignmentListView.as_view(), name="guard-my-shifts"),
    path("me/post-orders/", views.MyPostOrderListView.as_view(), name="guard-my-post-orders"),
    path("me/report-templates/", views.MyReportTemplateListView.as_view(), name="guard-my-report-templates"),
    path("me/availability/", views.MyAvailabilityListCreateView.as_view(), name="guard-my-availability"),
    path("me/leave-requests/", views.MyLeaveRequestListCreateView.as_view(), name="guard-my-leave-requests"),
    path("me/shift-swaps/", views.MyShiftSwapRequestListCreateView.as_view(), name="guard-my-shift-swaps"),
    path("me/timesheets/", views.MyTimesheetListView.as_view(), name="guard-my-timesheets"),
    path("me/shifts/<uuid:assignment_id>/clock/", views.MyClockEventCreateView.as_view(), name="guard-my-clock"),
    path("me/shifts/<uuid:assignment_id>/assets/", asset_views.MyShiftAssetManifestView.as_view(), name="guard-my-shift-assets"),
    path("me/shifts/<uuid:assignment_id>/assets/readiness/", asset_views.MyShiftAssetReadinessView.as_view(), name="guard-my-shift-assets-readiness"),
    path("me/shifts/<uuid:assignment_id>/assets/confirm-issue/", asset_views.MyShiftAssetConfirmView.as_view(), name="guard-my-shift-assets-confirm"),
    path("assignments/<uuid:assignment_id>/asset-manifest/build/", asset_views.ShiftAssetManifestBuildView.as_view(), name="guard-shift-asset-manifest-build"),
    path("me/shifts/<uuid:assignment_id>/<str:action>/", views.MyShiftAssignmentActionView.as_view(), name="guard-my-shift-action"),
    path("me/patrol-rounds/<uuid:patrol_round_id>/scan/", views.MyCheckpointScanCreateView.as_view(), name="guard-my-scan"),
    path("me/patrol-rounds/<uuid:patrol_round_id>/complete/", views.MyPatrolRoundCompleteView.as_view(), name="guard-my-patrol-complete"),
    path("me/reports/", views.MyFieldReportListCreateView.as_view(), name="guard-my-reports"),
    path("client/portal/", views.ClientPortalSnapshotView.as_view(), name="guard-client-portal"),
    path("client/reports/<uuid:report_id>/acknowledge/", views.ClientFieldReportAcknowledgeView.as_view(), name="guard-client-report-acknowledge"),
    path("me/location/", views.MyLocationPingCreateView.as_view(), name="guard-my-location"),
    path("me/panic/", views.MyPanicAlertCreateView.as_view(), name="guard-my-panic"),
    path("me/welfare-checks/", views.MyWelfareCheckListView.as_view(), name="guard-my-welfare-checks"),
    path("me/welfare-checks/<uuid:welfare_check_id>/confirm/", views.MyWelfareCheckConfirmView.as_view(), name="guard-my-welfare-confirm"),
    path("me/dispatch-tasks/", views.MyDispatchTaskListView.as_view(), name="guard-my-dispatch-tasks"),
    path("me/dispatch-tasks/<uuid:task_id>/<str:action>/", views.MyDispatchTaskTransitionView.as_view(), name="guard-my-dispatch-action"),
]
