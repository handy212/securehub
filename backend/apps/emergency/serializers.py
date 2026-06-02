from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.sites.models import CustomerSiteAccess

from .models import (
    AccountEmergencyService,
    EmergencyLocationUpdate,
    EmergencyRequest,
    EmergencyServiceStatus,
    SiteEmergencyService,
)


def _active_status_filter():
    return [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]


def user_has_emergency_entitlement(user, site=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if AccountEmergencyService.objects.filter(
        user=user,
        status__in=_active_status_filter(),
    ).exists():
        return True
    if site is not None:
        return SiteEmergencyService.objects.filter(
            site=site,
            status__in=_active_status_filter(),
        ).exists()
    accessible_site_ids = CustomerSiteAccess.objects.filter(user=user).values_list("site_id", flat=True)
    return SiteEmergencyService.objects.filter(
        site_id__in=accessible_site_ids,
        status__in=_active_status_filter(),
    ).exists()


class EmergencyLocationMixin(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=12, decimal_places=9)
    longitude = serializers.DecimalField(max_digits=12, decimal_places=9)
    accuracy_m = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    altitude_m = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    speed_mps = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    heading_deg = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    device_timestamp = serializers.DateTimeField(required=False, allow_null=True)

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class EmergencyRequestCreateSerializer(EmergencyLocationMixin, serializers.ModelSerializer):
    site_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = EmergencyRequest
        fields = (
            "site_id",
            "trigger_context",
            "latitude",
            "longitude",
            "accuracy_m",
            "altitude_m",
            "speed_mps",
            "heading_deg",
            "device_timestamp",
            "contact_phone",
            "note",
            "metadata",
        )
        extra_kwargs = {
            "trigger_context": {"required": False},
            "contact_phone": {"required": False, "allow_blank": True},
            "note": {"required": False, "allow_blank": True},
            "metadata": {"required": False},
        }

    def validate(self, attrs):
        from apps.sites.models import Site

        request = self.context["request"]
        site_id = attrs.pop("site_id", None)
        site = None
        if site_id:
            access = CustomerSiteAccess.objects.select_related("site").filter(
                user=request.user,
                site_id=site_id,
            ).first()
            if not access and not (request.user.is_staff or request.user.is_superuser):
                raise serializers.ValidationError({"site_id": "You do not have access to this site."})
            site = access.site if access else Site.objects.filter(id=site_id).first()
            if site is None:
                raise serializers.ValidationError({"site_id": "Unknown site."})
            try:
                if site.subscription.is_access_blocked():
                    raise serializers.ValidationError(
                        {"site_id": "This site's core subscription is suspended or cancelled."}
                    )
            except Site.subscription.RelatedObjectDoesNotExist:
                pass

        if not user_has_emergency_entitlement(request.user, site):
            raise serializers.ValidationError(
                {"emergency_service": "Emergency patrol support is not enabled for this account or site."}
            )

        attrs["site"] = site
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        if not validated_data.get("device_timestamp"):
            validated_data["device_timestamp"] = timezone.now()
        return EmergencyRequest.objects.create(customer=request.user, **validated_data)


class EmergencyLocationUpdateSerializer(EmergencyLocationMixin, serializers.ModelSerializer):
    class Meta:
        model = EmergencyLocationUpdate
        fields = (
            "id",
            "latitude",
            "longitude",
            "accuracy_m",
            "altitude_m",
            "speed_mps",
            "heading_deg",
            "device_timestamp",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class EmergencyRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.get_full_name", read_only=True)
    customer_username = serializers.CharField(source="customer.username", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    latest_location = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyRequest
        fields = (
            "id",
            "customer",
            "customer_name",
            "customer_username",
            "site",
            "site_name",
            "status",
            "trigger_context",
            "latitude",
            "longitude",
            "accuracy_m",
            "altitude_m",
            "speed_mps",
            "heading_deg",
            "device_timestamp",
            "contact_phone",
            "note",
            "metadata",
            "latest_location",
            "assigned_to",
            "assigned_at",
            "assignment_note",
            "acknowledged_by",
            "acknowledged_at",
            "dispatched_by",
            "dispatched_at",
            "arrived_at",
            "resolved_by",
            "resolved_at",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_latest_location(self, obj):
        update = obj.location_updates.order_by("-created_at").first()
        if update is None:
            return {
                "latitude": obj.latitude,
                "longitude": obj.longitude,
                "accuracy_m": obj.accuracy_m,
                "altitude_m": obj.altitude_m,
                "speed_mps": obj.speed_mps,
                "heading_deg": obj.heading_deg,
                "device_timestamp": obj.device_timestamp,
                "created_at": obj.created_at,
            }
        return EmergencyLocationUpdateSerializer(update).data


class EmergencyStatusSerializer(serializers.Serializer):
    account_enabled = serializers.BooleanField()
    site_enabled = serializers.BooleanField()
    enabled = serializers.BooleanField()
    sites = serializers.ListField()


class EmergencyTransitionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class EmergencyStaffRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name")
