from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.accounts.views import FCMDeviceView, ProfileView
from apps.alarms.views import SiteCommandListView, SiteEventListView, SubsystemCommandView
from apps.hik_adapter.views import (
    HikHealthView,
    HikWebhookConfigView,
    HikDeviceAddView,
    HikDeviceDeleteView,
    InstallerSearchView,
    ARCDeviceListView,
    ARCServiceView,
)
from apps.dashboard.api_views import SiteStatusPollView
from apps.sites.views import (
    AlarmPanelDeviceViewSet,
    SiteStatusView,
    SiteViewSet,
    SubsystemViewSet,
    ZoneViewSet,
)
from config.views import ApiRootView, HealthCheckView
from django.conf import settings


router = DefaultRouter()
router.register("sites", SiteViewSet, basename="site")
router.register("alarm-devices", AlarmPanelDeviceViewSet, basename="alarm-device")
router.register("subsystems", SubsystemViewSet, basename="subsystem")
router.register("zones", ZoneViewSet, basename="zone")

urlpatterns = [
    path("", RedirectView.as_view(url="/console/", permanent=False), name="service-root"),
    path("favicon.ico", RedirectView.as_view(url="/static/dashboard/logo.png", permanent=False)),
    path("healthz/", HealthCheckView.as_view(), name="health-check"),
    path("admin/", admin.site.urls),
    path("api/v1/integrations/hik/health/", HikHealthView.as_view(), name="hik-health"),
    path("api/v1/sites/<uuid:site_id>/poll/", SiteStatusPollView.as_view(), name="site-status-poll"),
    path("api/v1/sites/<uuid:site_id>/status/", SiteStatusView.as_view(), name="site-status"),
    path("api/v1/", include(router.urls)),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/profile/", ProfileView.as_view(), name="profile"),
    path(
        "api/v1/notifications/register-device/",
        FCMDeviceView.as_view(),
        name="fcm-register-device",
    ),
    path(
        "api/v1/sites/<uuid:site_id>/subsystems/<uuid:subsystem_id>/<str:action>/",
        SubsystemCommandView.as_view(),
        name="subsystem-command",
    ),
    path(
        "api/v1/sites/<uuid:site_id>/events/",
        SiteEventListView.as_view(),
        name="site-events",
    ),
    path(
        "api/v1/sites/<uuid:site_id>/commands/",
        SiteCommandListView.as_view(),
        name="site-commands",
    ),
    path("api/v1/hik/webhook-config/", HikWebhookConfigView.as_view(), name="hik-webhook-config"),
    path(
        "api/v1/hik/sites/<uuid:site_id>/devices/add/",
        HikDeviceAddView.as_view(),
        name="hik-device-add",
    ),
    path(
        "api/v1/hik/devices/<str:hik_device_id>/delete/",
        HikDeviceDeleteView.as_view(),
        name="hik-device-delete",
    ),
    path("api/v1/hik/installers/", InstallerSearchView.as_view(), name="hik-installers"),
    path("api/v1/hik/arc/devices/", ARCDeviceListView.as_view(), name="hik-arc-devices"),
    path("api/v1/hik/arc/<str:action>/", ARCServiceView.as_view(), name="hik-arc-service"),
    path("api/v1/alarms/", include("apps.alarms.urls")),
    path("api/v1/communication/", include("apps.communication.urls")),
    path("api/v1/emergency/", include("apps.emergency.urls")),
    path("api/v1/guarding/", include("apps.guarding.urls")),
    path("console/", include("apps.dashboard.urls")),
]

if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]

urlpatterns += staticfiles_urlpatterns()
