import logging
from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.alarms.firebase import get_firebase_messaging

logger = logging.getLogger(__name__)

MAX_MULTICAST_TOKENS = 500
INVALID_FCM_CODES = {
    "invalid-argument",
    "invalid-registration-token",
    "registration-token-not-registered",
    "unregistered",
}


@dataclass
class PushDeliveryResult:
    sent: int = 0
    failed: int = 0
    reason: str = ""

    def as_dict(self) -> dict:
        payload = {"sent": self.sent, "failed": self.failed}
        if self.reason:
            payload["reason"] = self.reason
        return payload


def normalize_push_data(data: dict | None) -> dict[str, str]:
    normalized = {}
    for key, value in (data or {}).items():
        if value is not None:
            normalized[str(key)] = str(value)
    return normalized


def _chunks(items: list, size: int = MAX_MULTICAST_TOKENS):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def is_invalid_fcm_exception(exc: Exception | None) -> bool:
    if exc is None:
        return False
    code = str(getattr(exc, "code", "") or "").lower()
    message = str(exc).lower()
    return code in INVALID_FCM_CODES or any(token in message for token in INVALID_FCM_CODES)


def active_devices_for_users(users: Iterable | QuerySet):
    from apps.accounts.models import FCMDevice

    return FCMDevice.objects.filter(user__in=users, is_active=True)


def active_devices_for_broadcast(message):
    from apps.accounts.models import FCMDevice

    if message.recipient:
        return FCMDevice.objects.filter(user=message.recipient, is_active=True)
    if message.recipient_group_id:
        return FCMDevice.objects.filter(
            user__customer_profile__group_id=message.recipient_group_id,
            user__customer_profile__is_mobile_user=True,
            is_active=True,
        )
    return FCMDevice.objects.filter(
        user__customer_profile__is_mobile_user=True,
        is_active=True,
    )


def send_push_to_devices(devices, *, title: str, body: str, data: dict | None = None) -> dict:
    """
    Send one notification payload to many registered devices.

    This is the central server-side push path for alarms, emergency events,
    guarding events, and operator broadcasts.
    """
    messaging = get_firebase_messaging()
    if messaging is None:
        logger.warning("FCM not configured - skipping push channel")
        return PushDeliveryResult(reason="FCM not configured").as_dict()

    device_rows = list(devices)
    token_by_device = [(device.pk, device.token) for device in device_rows if device.token]
    if not token_by_device:
        return PushDeliveryResult(reason="no active devices").as_dict()

    from apps.accounts.models import FCMDevice

    sent = failed = 0
    payload_data = normalize_push_data(data)
    for batch in _chunks(token_by_device):
        device_ids = [device_id for device_id, _token in batch]
        tokens = [token for _device_id, token in batch]
        multicast = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=payload_data,
            tokens=tokens,
        )
        try:
            response = messaging.send_each_for_multicast(multicast)
        except Exception as exc:
            logger.error("FCM multicast error: %s", exc)
            failed += len(tokens)
            continue

        sent += response.success_count
        failed += response.failure_count
        if response.failure_count:
            stale_ids = [
                device_ids[index]
                for index, item in enumerate(response.responses)
                if not item.success and is_invalid_fcm_exception(getattr(item, "exception", None))
            ]
            if stale_ids:
                FCMDevice.objects.filter(pk__in=stale_ids).update(is_active=False)

    return PushDeliveryResult(sent=sent, failed=failed).as_dict()


def send_push_to_users(users: Iterable | QuerySet, *, title: str, body: str, data: dict | None = None) -> dict:
    return send_push_to_devices(active_devices_for_users(users), title=title, body=body, data=data)


def send_push_to_user(user, *, title: str, body: str, data: dict | None = None) -> dict:
    User = get_user_model()
    return send_push_to_users(User.objects.filter(pk=user.pk), title=title, body=body, data=data)
