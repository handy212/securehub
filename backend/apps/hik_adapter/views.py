import logging

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.sites.models import Site

from .services import HikPartnerError, HikPartnerService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class AdminThrottle(UserRateThrottle):
    """Limits sensitive admin endpoints to 20 requests per minute per user."""
    rate = "20/min"


def _handle_hik_error(exc: Exception) -> None:
    """Log and re-raise a HikPartnerError as a DRF ValidationError."""
    logger.error("Hik-Partner error: %s", exc, exc_info=True)
    raise ValidationError({"detail": str(exc)}) from exc


def _safe_int(value, default: int) -> int:
    """Parse an integer query param safely; return default on bad input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class HikHealthView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        data = HikPartnerService().health()
        return Response({"success": True, "data": data})


class HikWebhookConfigView(APIView):
    """
    Manage the Hik-Partner Pro webhook push configuration (§3.67–§3.69).
    Restricted to superadmins — credentials and callback URLs are server-side only.

    GET    → query current config
    POST   → save/update config (callbackUrl required; must be HTTPS)
    DELETE → remove config
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    throttle_classes = [AdminThrottle]

    def _require_superuser(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("Only superadmins can manage webhook configuration.")

    def get(self, request):
        self._require_superuser(request)
        data = HikPartnerService().query_webhook_config()
        return Response({"success": True, "data": data})

    def post(self, request):
        self._require_superuser(request)
        callback_url = request.data.get("callbackUrl")
        if not callback_url:
            raise ValidationError({"callbackUrl": "This field is required."})
        if "signSecret" in request.data:
            raise ValidationError(
                {"signSecret": "Configure the webhook secret server-side via environment settings."}
            )

        try:
            data = HikPartnerService().save_webhook_config(
                callback_url=callback_url,
                retry_times=request.data.get("retryTimes", 3),
                retry_delay_ms=request.data.get("retryDelay", 1000),
            )
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        logger.info(
            "User %s updated webhook config: callbackUrl=%s",
            request.user.id, callback_url,
        )
        return Response({"success": True, "data": data}, status=201)

    def delete(self, request):
        self._require_superuser(request)
        try:
            HikPartnerService().delete_webhook_config()
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        logger.info("User %s deleted webhook config", request.user.id)
        return Response({"success": True, "message": "Webhook configuration deleted."})


class HikDeviceAddView(APIView):
    """
    Add one or more devices to a site on the Hik-Partner Pro platform (§3.18).
    Restricted to admins — requires the device serial number and the validation
    code printed on the device label.

    POST /api/v1/hik/sites/{site_id}/devices/add/
    Body: {"deviceList": [{"deviceSerial": "...", "validateCode": "...", "extendInfo": ""}]}

    After a successful add, local device records are synced automatically.
    The response includes addSuccessList and addFailedList from the Hik platform.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    throttle_classes = [AdminThrottle]

    def post(self, request, site_id):
        site = get_object_or_404(Site, id=site_id)

        device_list = request.data.get("deviceList")
        if not device_list or not isinstance(device_list, list):
            raise ValidationError({"deviceList": "A non-empty list of devices is required."})

        for entry in device_list:
            if not entry.get("deviceSerial") or not entry.get("validateCode"):
                raise ValidationError(
                    {"deviceList": "Each device must have deviceSerial and validateCode."}
                )

        try:
            result = HikPartnerService().add_devices_to_hik_site(site, device_list)
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        serials = [d.get("deviceSerial") for d in device_list]
        logger.info(
            "User %s added devices %s to site %s",
            request.user.id, serials, site.id,
        )
        return Response({"success": True, "data": result}, status=201)


class HikDeviceDeleteView(APIView):
    """
    Remove a device from the Hik-Partner Pro platform and from local records (§3.19).
    Restricted to admins.

    POST /api/v1/hik/devices/{hik_device_id}/delete/
    No request body needed — the Hik device ID is taken from the URL.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    throttle_classes = [AdminThrottle]

    def post(self, request, hik_device_id):
        try:
            HikPartnerService().remove_device_from_hik(hik_device_id)
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        logger.info(
            "User %s deleted device hik_device_id=%s",
            request.user.id, hik_device_id,
        )
        return Response({
            "success": True,
            "message": "Device deleted.",
            "hik_device_id": hik_device_id,
        })


class InstallerSearchView(APIView):
    """
    Search for employees/installers on the Hik-Partner Pro platform (§3.2).
    Restricted to admins — used to look up installer IDs for site assignment.

    GET /api/v1/hik/installers/?q=name&page=1&page_size=20
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        search = request.query_params.get("q", "")
        page = _safe_int(request.query_params.get("page"), 1)
        page_size = _safe_int(request.query_params.get("page_size"), 20)

        try:
            data = HikPartnerService().search_installers(
                search=search, page=page, page_size=page_size
            )
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        return Response({"success": True, "data": data})


class ARCDeviceListView(APIView):
    """
    List devices with ARC (Alarm Receiving Centre) service enabled (§3.37).
    Restricted to admins.

    GET /api/v1/hik/arc/devices/?site_id=...&page=1
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        site_id = request.query_params.get("site_id")
        page = _safe_int(request.query_params.get("page"), 1)
        page_size = _safe_int(request.query_params.get("page_size"), 20)

        try:
            data = HikPartnerService().list_arc_devices(
                page=page, page_size=page_size, site_id=site_id
            )
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        return Response({"success": True, "data": data})


class ARCServiceView(APIView):
    """
    Enable or disable ARC service for a device (§3.38–3.39).
    Restricted to admins.

    POST /api/v1/hik/arc/enable/  — body: {"deviceSerial": "...", "arcId": "..."}
    POST /api/v1/hik/arc/disable/ — body: {"deviceSerial": "..."}
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    throttle_classes = [AdminThrottle]

    def post(self, request, action):
        if action not in {"enable", "disable"}:
            raise ValidationError({"action": "Must be 'enable' or 'disable'."})

        device_serial = request.data.get("deviceSerial")
        if not device_serial:
            raise ValidationError({"deviceSerial": "This field is required."})

        service = HikPartnerService()

        try:
            if action == "enable":
                arc_id = request.data.get("arcId")
                if not arc_id:
                    raise ValidationError({"arcId": "This field is required to enable ARC."})
                result = service.enable_arc_for_device(
                    device_serial=device_serial, arc_id=arc_id
                )
                logger.info(
                    "User %s enabled ARC for device %s (arcId=%s)",
                    request.user.id, device_serial, arc_id,
                )
                return Response({"success": True, "data": result}, status=201)

            service.disable_arc_for_device(device_serial=device_serial)
        except HikPartnerError as exc:
            _handle_hik_error(exc)

        logger.info(
            "User %s disabled ARC for device %s",
            request.user.id, device_serial,
        )
        return Response({
            "success": True,
            "message": "ARC service disabled.",
            "deviceSerial": device_serial,
        })
