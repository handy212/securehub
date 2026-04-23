from rest_framework import serializers

from apps.alarms.event_labels import humanize_event_label
from apps.sites.models import Zone
from .models import AlarmEvent, ArmDisarmCommand


class AlarmEventSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    event_name = serializers.SerializerMethodField()
    normalized_event_type = serializers.SerializerMethodField()

    # Enriched zone/subsystem fields — eliminates raw UUID display on clients
    zone_name = serializers.SerializerMethodField()
    zone_number = serializers.SerializerMethodField()
    zone_detector_type = serializers.SerializerMethodField()
    subsystem_name = serializers.SerializerMethodField()

    # Tells clients up-front whether this event has media (footage/photos)
    # without requiring a separate picture endpoint call.
    has_media = serializers.SerializerMethodField()

    class Meta:
        model = AlarmEvent
        fields = (
            "id",
            "site_name",
            "event_type",
            "event_name",
            "normalized_event_type",
            "event_category",
            "severity",
            "payload",
            "occurred_at",
            "subsystem",
            "subsystem_name",
            "zone",
            "zone_name",
            "zone_number",
            "zone_detector_type",
            "performed_by",
            "has_media",
            "acknowledged",
        )

    def get_zone_name(self, obj: AlarmEvent) -> str | None:
        z = obj.zone
        return z.name if z else None

    def get_zone_number(self, obj: AlarmEvent) -> int | None:
        z = obj.zone
        return z.zone_number if z else None

    def get_zone_detector_type(self, obj: AlarmEvent) -> str | None:
        z = obj.zone
        return z.display_type if z else None

    def get_subsystem_name(self, obj: AlarmEvent) -> str | None:
        s = obj.subsystem
        return s.name if s else None

    def get_has_media(self, obj: AlarmEvent) -> bool:
        """True if this event has at least one picture/video attachment stored in its payload."""
        pictures = obj.payload.get("pictures", [])
        if pictures:
            return True
        # Also check alarmData.pictureList (for events ingested via webhook before pictures extraction)
        alarm_data = obj.payload.get("alarmData", {})
        if isinstance(alarm_data, dict):
            return bool(alarm_data.get("pictureList"))
        return False

    def get_event_name(self, obj: AlarmEvent) -> str:
        return humanize_event_label(obj.payload.get("event_name") or obj.event_type)

    def get_normalized_event_type(self, obj: AlarmEvent) -> str:
        return obj.payload.get("normalized_event_type") or ""


class ArmDisarmCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmDisarmCommand
        fields = (
            "id",
            "site",
            "subsystem",
            "action",
            "idempotency_key",
            "status",
            "request_payload",
            "response_payload",
            "failure_reason",
            "created_at",
        )


class SubsystemCommandRequestSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=False,
    )
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    metadata = serializers.DictField(required=False, default=dict)
    # Optional AX Pro user credentials — forwarded as X-Username / X-Password ISAPI headers
    operator_username = serializers.CharField(max_length=64, required=False, allow_blank=False)
    operator_password = serializers.CharField(max_length=64, required=False, allow_blank=False)
    # AX Pro partition-specific operate code (device-defined, forwarded in ISAPI body)
    moduleOperateCode = serializers.CharField(max_length=64, required=False, allow_blank=False)
