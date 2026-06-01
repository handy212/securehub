import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hik_adapter.services import HikPartnerService
from apps.sites.models import AlarmPanelDevice, CustomerSiteAccess, Site, Subsystem, Zone
from apps.sites.permissions import CanControlAlarm, HasSiteAccess, IsSubscriptionActive

from .media import collect_related_event_media, resolve_picture_media_type
from .models import AlarmEvent, ArmDisarmCommand
from .serializers import (
    AlarmEventSerializer,
    ArmDisarmCommandSerializer,
    SubsystemCommandRequestSerializer,
)
from .tasks import dispatch_alarm_notifications, process_webhook_messages

logger = logging.getLogger(__name__)


class SiteEventListView(ListAPIView):
    serializer_class = AlarmEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, HasSiteAccess]

    def get_queryset(self):
        site = get_object_or_404(Site, id=self.kwargs["site_id"])
        return (
            AlarmEvent.objects.filter(site=site)
            .select_related("site", "subsystem", "zone")
            .order_by("-occurred_at")
        )


class GlobalEventListView(ListAPIView):
    serializer_class = AlarmEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_queryset(self):
        accessible_site_ids = CustomerSiteAccess.objects.filter(
            user=self.request.user
        ).values_list("site_id", flat=True)
        return (
            AlarmEvent.objects.filter(site_id__in=accessible_site_ids)
            .select_related("site", "subsystem", "zone")
            .order_by("-occurred_at")
        )


class SiteCommandListView(ListAPIView):
    serializer_class = ArmDisarmCommandSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, HasSiteAccess]

    def get_queryset(self):
        site = get_object_or_404(Site, id=self.kwargs["site_id"])
        return (
            ArmDisarmCommand.objects.filter(site=site)
            .select_related("subsystem", "requested_by")
            .order_by("-created_at")
        )


class SubsystemCommandView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, CanControlAlarm]
    allowed_actions = {"arm", "disarm", "stay-arm", "clear-alarm"}

    def post(self, request, site_id, subsystem_id, action):
        if action not in self.allowed_actions:
            raise ValidationError({"action": "Unsupported alarm action."})

        serializer = SubsystemCommandRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "SubsystemCommandView: Serializer validation failed for %s: %s",
                action, serializer.errors
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        site = get_object_or_404(Site, id=site_id)

        subsystem = get_object_or_404(
            Subsystem.objects.select_related("device", "site"),
            id=subsystem_id,
            site=site,
        )
        if not subsystem.device.is_online:
            return Response(
                {
                    "command": "Panel is offline or unreachable. Refresh status after the panel reconnects.",
                    "code": "panel_offline",
                },
                status=status.HTTP_409_CONFLICT,
            )
        validated_payload = serializer.validated_data
        idempotency_key = validated_payload.get(
            "idempotency_key",
            request.headers.get("X-Idempotency-Key", ""),
        )

        if idempotency_key:
            existing_command = (
                ArmDisarmCommand.objects.filter(
                    site=site,
                    subsystem=subsystem,
                    requested_by=request.user,
                    action=action,
                    idempotency_key=idempotency_key,
                )
                .order_by("-created_at")
                .first()
            )
            if existing_command:
                return Response(
                    ArmDisarmCommandSerializer(existing_command).data,
                    status=status.HTTP_200_OK,
                )

        # Mask operator password before persisting — never store plaintext credentials
        stored_payload = {**validated_payload}
        if stored_payload.get("operator_password"):
            stored_payload["operator_password"] = "***"

        try:
            command = ArmDisarmCommand.objects.create(
                site=site,
                subsystem=subsystem,
                requested_by=request.user,
                action=action,
                idempotency_key=idempotency_key,
                device_serial=subsystem.device.serial_number,
                request_payload=stored_payload,
            )
        except IntegrityError:
            if idempotency_key:
                existing_command = (
                    ArmDisarmCommand.objects.filter(
                        site=site,
                        idempotency_key=idempotency_key,
                    )
                    .order_by("-created_at")
                    .first()
                )
                if existing_command:
                    return Response(
                        ArmDisarmCommandSerializer(existing_command).data,
                        status=status.HTTP_200_OK,
                    )
            raise

        try:
            response_payload = HikPartnerService().execute_subsystem_command(
                site=site,
                subsystem=subsystem,
                action=action,
                payload=validated_payload,
                requesting_user=request.user,
            )
            command.status = ArmDisarmCommand.STATUS_SUCCESS
            command.response_payload = response_payload
            command.failure_reason = ""
            command.executed_at = timezone.now()
            command.save(
                update_fields=[
                    "status",
                    "response_payload",
                    "failure_reason",
                    "executed_at",
                    "updated_at",
                ]
            )
            return Response(
                ArmDisarmCommandSerializer(command).data,
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as exc:
            logger.error(
                "SubsystemCommandView: Command execution failed for %s: %s",
                action, exc, exc_info=True
            )
            command.status = ArmDisarmCommand.STATUS_FAILED
            command.failure_reason = str(exc)
            command.save(update_fields=["status", "failure_reason", "updated_at"])
            if getattr(exc, "error_code", None) == "LAP020011":
                return Response(
                    {
                        "command": "Panel is offline or unreachable. Refresh status after the panel reconnects.",
                        "code": "panel_offline",
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            raise ValidationError({"command": str(exc)}) from exc


class AlarmPictureURLView(APIView):
    """
    Retrieve download URL(s) for alarm image attachments. Per API guide §3.36.

    Handles two event types:
    - Linkage (PIR cameras with built-in cam): images are in alarmData.pictureList[].url
      - https:// URLs → returned directly (no Hik API call needed)
      - ISAPI_FILES/... URLs → resolved via /v1/alarm/pictureurl (valid 2 hours)
    - Other events: accepts explicit filePath in request body.

    POST body (optional): {"filePath": "ISAPI_FILES/..."}
    Returns: {"pictures": [{url, encrypt, id}]} or error if no pictures found.
    """

    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, HasSiteAccess]

    def post(self, request, site_id, event_id):
        from apps.hik_adapter.services import HikPartnerService

        site = get_object_or_404(Site, id=site_id)
        event = get_object_or_404(AlarmEvent, id=event_id, site=site)

        service = HikPartnerService()

        # Caller can always pass an explicit filePath to override auto-detection
        explicit_path = request.data.get("filePath")
        if explicit_path:
            result = service.get_alarm_picture_url(explicit_path)
            return Response({"pictures": [{"url": result.get("pictureUrl"), "encrypt": result.get("encrypt")}]})

        stored_pictures = collect_related_event_media(event)
        if not stored_pictures:
            raise ValidationError({
                "detail": "No pictures found for this event. "
                          "Provide filePath explicitly if the image path is known."
            })

        # Resolve each picture URL
        resolved = []
        for pic in stored_pictures:
            url = pic.get("url", "")
            media_id = pic.get("id", "")
            alarm_data = pic.get("alarm_data") or {}
            if pic.get("needs_url_fetch") or url.startswith("ISAPI_FILES"):
                fetch_result = service.get_alarm_picture_url(url)
                real_url = fetch_result.get("pictureUrl", "")
                media_type = resolve_picture_media_type(
                    url=real_url,
                    media_id=media_id,
                    stored_type=pic.get("type", ""),
                    alarm_data=alarm_data,
                    probe_remote=True,
                )
                resolved.append({
                    "id": media_id,
                    "url": real_url,
                    "encrypt": fetch_result.get("encrypt", False),
                    "type": media_type,
                })
            else:
                # Direct https:// URL — no API call needed
                media_type = resolve_picture_media_type(
                    url=url,
                    media_id=media_id,
                    stored_type=pic.get("type", ""),
                    alarm_data=alarm_data,
                    probe_remote=True,
                )
                resolved.append({
                    "id": media_id,
                    "url": url,
                    "encrypt": "isEncrypted=1" in url,
                    "type": media_type,
                })

        return Response({"pictures": resolved})


class HikWebhookView(APIView):
    """
    Endpoint to receive push notifications from Hik-Partner Pro.
    Signature algorithm per API guide §2.10:
      sha256=HMAC-SHA256(signSecret, "{X-Hook-Timestamp}.{batchId}")
    """
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _extract_messages(event_data):
        if isinstance(event_data, list):
            return event_data
        if not isinstance(event_data, dict):
            return []

        raw = event_data.get("list")
        if raw is None:
            data = event_data.get("data")
            if isinstance(data, dict):
                raw = data.get("list")
            elif data is not None:
                raw = data

        if raw is None:
            raw = [event_data]
        return raw if isinstance(raw, list) else [raw]

    def get(self, request, *args, **kwargs):
        """
        Webhook validation handshake — per API guide §2.10.
        The platform sends a GET request with X-Hook-Timestamp and X-Hook-Batch-Id.
        We must respond with the same timestamp and batch_id signed with our secret
        in the X-Hook-Signature header.
        """
        timestamp = request.headers.get("X-Hook-Timestamp", "")
        batch_id = request.headers.get("X-Hook-Batch-Id", "")
        
        if not timestamp or not batch_id:
            return Response(
                {"code": "1", "msg": "Missing verification headers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reuse signature logic to generate the required header
        secret = HikPartnerService.get_webhook_sign_secret().encode("utf-8")
        message = f"{timestamp}.{batch_id}".encode("utf-8")
        signature = "sha256=" + hmac.new(secret, message, hashlib.sha256).hexdigest()

        logger.info(
            "Webhook GET Handshake: timestamp=%s, batch_id=%s -> signature generated",
            timestamp, batch_id
        )

        return Response(
            {"code": "0", "msg": "ready"},
            status=status.HTTP_200_OK,
            headers={"X-Hook-Signature": signature}
        )

    def _verify_signature(self, request) -> bool:
        """Return True if X-Hook-Signature is valid and timestamp is fresh."""
        signature_header = request.headers.get("X-Hook-Signature", "")
        timestamp = request.headers.get("X-Hook-Timestamp", "")
        batch_id = request.headers.get("X-Hook-Batch-Id", "")

        logger.debug(
            "Webhook Verification: signature=%s timestamp=%s batch_id=%s",
            signature_header,
            timestamp,
            batch_id,
        )

        if not signature_header or not timestamp or not batch_id:
            logger.warning("Webhook Verification: missing signature, timestamp, or batch id")
            return False

        # Reject requests older than 1 minute per Hik webhook guidance.
        try:
            diff = abs(time.time() * 1000 - int(timestamp))
            if diff > 60_000:
                logger.warning("Webhook Verification: timestamp too old (diff=%dms)", diff)
                return False
        except (ValueError, TypeError):
            logger.warning("Webhook Verification: invalid timestamp")
            return False

        secret = HikPartnerService.get_webhook_sign_secret().encode("utf-8")
        
        message = f"{timestamp}.{batch_id}".encode("utf-8")
        expected = "sha256=" + hmac.new(secret, message, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected, signature_header):
            logger.warning(
                "Webhook Verification: signature MISMATCH. got=%s, expected_one=%s",
                signature_header,
                expected,
            )
            return False

        return True

    def post(self, request, *args, **kwargs):
        if not self._verify_signature(request):
            logger.warning("Webhook signature failed — rejecting request.")
            return Response(
                {"code": "1", "msg": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        request_id = str(__import__("uuid").uuid4())[:8]
        event_data = request.data
        header_batch_id = request.headers.get("X-Hook-Batch-Id", "")

        if isinstance(event_data, dict):
            body_batch_id = event_data.get("batchId")
            if body_batch_id and str(body_batch_id) != header_batch_id:
                logger.warning(
                    "WEBHOOK[%s]: batch id mismatch header=%s body=%s",
                    request_id,
                    header_batch_id,
                    body_batch_id,
                )
                return Response(
                    {"code": "1", "msg": "Batch id mismatch"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Safe message extraction — handle list, dict wrapper, nested data/list,
        # or a single event. Hik webhook bodies include batchId beside list.
        messages = self._extract_messages(event_data)

        # Filter out non-dict and empty entries
        messages = [m for m in messages if isinstance(m, dict) and m]
        logger.info(
            "WEBHOOK[%s]: received batch of %d message(s)",
            request_id, len(messages),
        )

        if not messages:
            return Response({"code": "0", "msg": "empty batch"})

        # Return immediately — offload all DB/service work to a worker.
        # This keeps the HTTP response under 1 s, preventing Hik-Partner Pro
        # from timing out and re-sending the same batch.
        process_webhook_messages.delay(messages)
        return Response({"code": "0", "msg": "accepted"})

    def _handle_partition_status(self, data):
        hik_site_id = data.get("siteId")
        hik_subsystem_id = data.get("partitionId")
        status_code = data.get("status")  # 1: Armed, 0: Disarmed

        # Match by site and subsystem number (partitionId usually comes as integer 1, 2...)
        subsystem = Subsystem.objects.filter(
            site__hik_site_id=hik_site_id,
            subsystem_number=hik_subsystem_id,
        ).select_related("site").first()

        if subsystem:
            subsystem.status = (
                Subsystem.STATUS_ARMED if status_code == 1 else Subsystem.STATUS_DISARMED
            )
            subsystem.save(update_fields=["status", "updated_at"])
            return AlarmEvent.objects.create(
                site=subsystem.site,
                subsystem=subsystem,
                event_type="arm_status_update",
                source_event_id=data.get("eventId", ""),
                payload=data,
                occurred_at=timezone.now(),
            )
        return None

    def _handle_zone_status(self, data):
        """Update zone state from webhook and record an alarm event."""
        hik_site_id = data.get("siteId")
        hik_subsystem_id = data.get("partitionId")
        zone_number = data.get("zoneNo")
        # status: 0=normal, 1=open, 2=alarm, 3=bypassed
        status_map = {
            0: Zone.STATE_NORMAL,
            1: Zone.STATE_OPEN,
            2: Zone.STATE_ALARM,
            3: Zone.STATE_BYPASSED,
        }
        new_state = status_map.get(data.get("status"))
        if new_state is None or zone_number is None:
            logger.warning("_handle_zone_status: missing status or zoneNo in payload")
            return

        zone = Zone.objects.filter(
            subsystem__site__hik_site_id=hik_site_id,
            subsystem__subsystem_number=hik_subsystem_id,
            zone_number=zone_number,
        ).select_related("subsystem__site").first()

        if zone:
            zone.state = new_state
            zone.save(update_fields=["state", "updated_at"])
            return AlarmEvent.objects.create(
                site=zone.subsystem.site,
                subsystem=zone.subsystem,
                zone=zone,
                event_type="zone_status_update",
                source_event_id=data.get("eventId", ""),
                payload=data,
                occurred_at=timezone.now(),
            )
        return None

    def _handle_device_status(self, data):
        """Update alarm panel device and video device online status from webhook."""
        hik_device_id = data.get("deviceId")
        # onlineStatus: 1=online, 0=offline
        is_online = data.get("onlineStatus") == 1
        now = timezone.now()

        AlarmPanelDevice.objects.filter(
            hik_device_id=hik_device_id
        ).update(is_online=is_online, last_seen_at=now if is_online else None)
