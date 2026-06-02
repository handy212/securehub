from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sites.models import CustomerSiteAccess, Site
from apps.sites.permissions import IsSubscriptionActive, get_accessible_site_ids_for_user

from .models import (
    AccountEmergencyService,
    EmergencyLocationUpdate,
    EmergencyRequest,
    EmergencyServiceStatus,
    SiteEmergencyService,
)
from .serializers import (
    EmergencyLocationUpdateSerializer,
    EmergencyRequestCreateSerializer,
    EmergencyRequestSerializer,
    EmergencyTransitionSerializer,
    user_has_emergency_entitlement,
)
from .tasks import dispatch_emergency_notifications


class EmergencyStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get(self, request):
        site_id = request.query_params.get("site_id")
        site = None
        if site_id:
            site = get_object_or_404(Site, id=site_id)
            if not request.user.is_staff and not request.user.is_superuser:
                if not CustomerSiteAccess.objects.filter(user=request.user, site=site).exists():
                    raise PermissionDenied("You do not have access to this site.")

        active_statuses = [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]
        account_enabled = AccountEmergencyService.objects.filter(
            user=request.user,
            status__in=active_statuses,
        ).exists()
        accessible_site_ids = get_accessible_site_ids_for_user(request.user)
        site_services = SiteEmergencyService.objects.filter(
            site_id__in=accessible_site_ids,
            status__in=active_statuses,
        ).select_related("site")
        sites = [
            {
                "id": str(service.site.id),
                "name": service.site.name,
                "enabled": True,
                "status": service.status,
                "monthly_rate": str(service.monthly_rate),
            }
            for service in site_services
        ]
        site_enabled = (
            SiteEmergencyService.objects.filter(site=site, status__in=active_statuses).exists()
            if site is not None
            else bool(sites)
        )
        return Response(
            {
                "account_enabled": account_enabled,
                "site_enabled": site_enabled,
                "enabled": account_enabled or site_enabled,
                "sites": sites,
            }
        )


class EmergencyRequestListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EmergencyRequestCreateSerializer
        return EmergencyRequestSerializer

    def get_queryset(self):
        qs = EmergencyRequest.objects.select_related(
            "customer",
            "site",
            "acknowledged_by",
            "dispatched_by",
            "resolved_by",
        ).prefetch_related("location_updates")
        if self.request.user.is_staff or self.request.user.is_superuser:
            return qs
        accessible_site_ids = get_accessible_site_ids_for_user(self.request.user)
        return qs.filter(customer=self.request.user) | qs.filter(site_id__in=accessible_site_ids)

    def perform_create(self, serializer):
        emergency = serializer.save()
        EmergencyLocationUpdate.objects.create(
            emergency_request=emergency,
            latitude=emergency.latitude,
            longitude=emergency.longitude,
            accuracy_m=emergency.accuracy_m,
            altitude_m=emergency.altitude_m,
            speed_mps=emergency.speed_mps,
            heading_deg=emergency.heading_deg,
            device_timestamp=emergency.device_timestamp,
        )
        dispatch_emergency_notifications.delay(str(emergency.id))
        return emergency

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emergency = self.perform_create(serializer)
        return Response(EmergencyRequestSerializer(emergency).data, status=status.HTTP_201_CREATED)


class EmergencyLocationUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def post(self, request, request_id):
        emergency = get_object_or_404(EmergencyRequest, id=request_id)
        if not self._can_update(request.user, emergency):
            raise PermissionDenied("You cannot update this emergency request.")
        if not emergency.is_active:
            raise ValidationError({"status": "Location updates are only accepted for active emergency requests."})
        if not user_has_emergency_entitlement(request.user, emergency.site):
            raise PermissionDenied("Emergency patrol support is not enabled.")

        serializer = EmergencyLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update = serializer.save(emergency_request=emergency)
        emergency.latitude = update.latitude
        emergency.longitude = update.longitude
        emergency.accuracy_m = update.accuracy_m
        emergency.altitude_m = update.altitude_m
        emergency.speed_mps = update.speed_mps
        emergency.heading_deg = update.heading_deg
        emergency.device_timestamp = update.device_timestamp
        emergency.save(
            update_fields=[
                "latitude",
                "longitude",
                "accuracy_m",
                "altitude_m",
                "speed_mps",
                "heading_deg",
                "device_timestamp",
                "updated_at",
            ]
        )
        return Response(EmergencyLocationUpdateSerializer(update).data, status=status.HTTP_201_CREATED)

    def _can_update(self, user, emergency):
        if user.is_staff or user.is_superuser:
            return True
        return emergency.customer_id == user.id


class EmergencyCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def post(self, request, request_id):
        emergency = get_object_or_404(EmergencyRequest, id=request_id)
        if emergency.customer_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("You cannot cancel this emergency request.")
        if emergency.status in {EmergencyRequest.STATUS_RESOLVED, EmergencyRequest.STATUS_CANCELLED}:
            raise ValidationError({"status": "This emergency request is already closed."})
        serializer = EmergencyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emergency.transition(
            EmergencyRequest.STATUS_CANCELLED,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(EmergencyRequestSerializer(emergency).data)


class EmergencyStaffTransitionView(APIView):
    permission_classes = [permissions.IsAdminUser]
    allowed_actions = {
        "acknowledge": EmergencyRequest.STATUS_ACKNOWLEDGED,
        "dispatch": EmergencyRequest.STATUS_DISPATCHED,
        "arrive": EmergencyRequest.STATUS_ARRIVED,
        "resolve": EmergencyRequest.STATUS_RESOLVED,
        "cancel": EmergencyRequest.STATUS_CANCELLED,
    }

    def post(self, request, request_id, action):
        if action not in self.allowed_actions:
            raise ValidationError({"action": "Unsupported emergency action."})
        emergency = get_object_or_404(EmergencyRequest, id=request_id)
        serializer = EmergencyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emergency.transition(
            self.allowed_actions[action],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(EmergencyRequestSerializer(emergency).data)
