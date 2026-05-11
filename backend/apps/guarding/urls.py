from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register("applicants", views.GuardApplicantViewSet, basename="guard-applicant")
router.register("workflow-events", views.GuardingEventLogViewSet, basename="guarding-workflow-event")
router.register("guards", views.GuardProfileViewSet, basename="guard-profile")
router.register("credentials", views.GuardCredentialViewSet, basename="guard-credential")
router.register("documents", views.GuardDocumentViewSet, basename="guard-document")
router.register("posts", views.GuardPostViewSet, basename="guard-post")
router.register("post-orders", views.PostOrderViewSet, basename="post-order")
router.register("shifts", views.ShiftViewSet, basename="guard-shift")
router.register("assignments", views.ShiftAssignmentViewSet, basename="guard-shift-assignment")
router.register("clock-events", views.ClockEventViewSet, basename="guard-clock-event")
router.register("checkpoints", views.CheckpointViewSet, basename="guard-checkpoint")
router.register("patrol-routes", views.PatrolRouteViewSet, basename="guard-patrol-route")
router.register("patrol-route-checkpoints", views.PatrolRouteCheckpointViewSet, basename="guard-patrol-route-checkpoint")
router.register("patrol-rounds", views.PatrolRoundViewSet, basename="guard-patrol-round")
router.register("checkpoint-scans", views.CheckpointScanViewSet, basename="guard-checkpoint-scan")
router.register("reports", views.FieldReportViewSet, basename="guard-field-report")
router.register("location-pings", views.GuardLocationPingViewSet, basename="guard-location-ping")
router.register("welfare-checks", views.WelfareCheckViewSet, basename="guard-welfare-check")
router.register("panic-alerts", views.GuardPanicAlertViewSet, basename="guard-panic-alert")
router.register("dispatch-tasks", views.DispatchTaskViewSet, basename="guard-dispatch-task")

urlpatterns = [
    path("", include(router.urls)),
    path("me/shifts/", views.MyShiftAssignmentListView.as_view(), name="guard-my-shifts"),
    path("me/shifts/<uuid:assignment_id>/clock/", views.MyClockEventCreateView.as_view(), name="guard-my-clock"),
    path("me/shifts/<uuid:assignment_id>/<str:action>/", views.MyShiftAssignmentActionView.as_view(), name="guard-my-shift-action"),
    path("me/patrol-rounds/<uuid:patrol_round_id>/scan/", views.MyCheckpointScanCreateView.as_view(), name="guard-my-scan"),
    path("me/patrol-rounds/<uuid:patrol_round_id>/complete/", views.MyPatrolRoundCompleteView.as_view(), name="guard-my-patrol-complete"),
    path("me/reports/", views.MyFieldReportListCreateView.as_view(), name="guard-my-reports"),
    path("me/location/", views.MyLocationPingCreateView.as_view(), name="guard-my-location"),
    path("me/panic/", views.MyPanicAlertCreateView.as_view(), name="guard-my-panic"),
    path("me/welfare-checks/<uuid:welfare_check_id>/confirm/", views.MyWelfareCheckConfirmView.as_view(), name="guard-my-welfare-confirm"),
    path("me/dispatch-tasks/", views.MyDispatchTaskListView.as_view(), name="guard-my-dispatch-tasks"),
    path("me/dispatch-tasks/<uuid:task_id>/<str:action>/", views.MyDispatchTaskTransitionView.as_view(), name="guard-my-dispatch-action"),
]
