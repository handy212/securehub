from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from apps.hik_adapter.services import HikPartnerService

from .models import AlarmPanelDevice, Site, Subsystem, Zone
from .permissions import HasSiteAccess, IsSubscriptionActive, get_accessible_site_ids_for_user
from .serializers import (
    AlarmPanelDeviceSerializer,
    SiteSerializer,
    SiteStatusSerializer,
    SubsystemSerializer,
    ZoneSerializer,
)


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, HasSiteAccess]

    def get_permissions(self):
        if getattr(self, "action", None) == "sync":
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        return SiteSerializer

    def get_queryset(self):
        return (
            Site.objects.filter(id__in=get_accessible_site_ids_for_user(self.request.user))
            .distinct()
            .order_by("id")
            .prefetch_related("devices__subsystems__zones")
        )

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        site = self.get_object()
        result = HikPartnerService().sync_site_devices(site)
        return Response(result)


class AlarmPanelDeviceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlarmPanelDeviceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_queryset(self):
        accessible_site_ids = get_accessible_site_ids_for_user(self.request.user)
        return (
            AlarmPanelDevice.objects.filter(site_id__in=accessible_site_ids)
            .select_related("site")
            .prefetch_related("subsystems__zones")
        )


class SubsystemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubsystemSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_queryset(self):
        accessible_site_ids = get_accessible_site_ids_for_user(self.request.user)
        return (
            Subsystem.objects.filter(site_id__in=accessible_site_ids)
            .select_related("site", "device")
            .prefetch_related("zones")
        )


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_queryset(self):
        accessible_site_ids = get_accessible_site_ids_for_user(self.request.user)
        return Zone.objects.filter(
            subsystem__site_id__in=accessible_site_ids
        ).select_related("subsystem__site")


class SiteStatusView(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, HasSiteAccess]
    serializer_class = SiteStatusSerializer
    lookup_url_kwarg = "site_id"

    def get(self, request, *args, **kwargs):
        site = get_object_or_404(Site, id=kwargs["site_id"])
        service = HikPartnerService()
        # Refresh partition and zone state from the device before reading local DB.
        # Errors are non-fatal — stale local state is returned if the device is unreachable.
        service.sync_alarm_status(site)
        site_status = service.get_site_status(site=site)
        serializer = self.get_serializer(site_status)
        return Response(serializer.data)
