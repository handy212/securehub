import logging
import base64
import json
from urllib import request as urllib_request

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmergencyNotificationDelivery, EmergencyRequest

logger = logging.getLogger(__name__)


def _staff_recipients():
    User = get_user_model()
    return list(User.objects.filter(is_active=True, is_staff=True))


def _create_delivery(emergency, *, channel, recipient, provider=""):
    return EmergencyNotificationDelivery.objects.create(
        emergency_request=emergency,
        channel=channel,
        recipient=recipient,
        provider=provider,
    )


def _mark(delivery, status, error=""):
    delivery.status = status
    delivery.last_error = error
    if status == EmergencyNotificationDelivery.STATUS_SENT:
        delivery.sent_at = timezone.now()
    delivery.save(update_fields=["status", "last_error", "sent_at"])


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_emergency_notifications(self, emergency_id: str) -> dict:
    try:
        emergency = EmergencyRequest.objects.select_related("customer", "site").get(id=emergency_id)
    except EmergencyRequest.DoesNotExist:
        return {"skipped": True, "reason": "emergency not found"}

    recipients = _staff_recipients()
    sent = failed = skipped = 0
    errors = []

    for user in recipients:
        title = "Emergency request"
        body = _body_for(emergency)
        data = {
            "type": "emergency",
            "emergency_id": str(emergency.id),
            "site_id": str(emergency.site_id or ""),
            "latitude": str(emergency.latitude),
            "longitude": str(emergency.longitude),
        }

        push_delivery = _create_delivery(
            emergency,
            channel="push",
            provider="firebase",
            recipient=user.email or user.username,
        )
        try:
            from apps.alarms.tasks import _send_generic_fcm_notification

            push_count = _send_generic_fcm_notification(user, title, body, data)
            _mark(push_delivery, EmergencyNotificationDelivery.STATUS_SENT if push_count else EmergencyNotificationDelivery.STATUS_SKIPPED)
            sent += 1 if push_count else 0
            skipped += 0 if push_count else 1
        except Exception as exc:
            _mark(push_delivery, EmergencyNotificationDelivery.STATUS_FAILED, str(exc))
            failed += 1
            errors.append(exc)

        if user.email:
            email_delivery = _create_delivery(
                emergency,
                channel="email",
                provider="django",
                recipient=user.email,
            )
            try:
                send_mail(
                    subject=f"[SecureHub Emergency] {emergency.customer.get_username()} needs support",
                    message=_email_message(emergency),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                _mark(email_delivery, EmergencyNotificationDelivery.STATUS_SENT)
                sent += 1
            except Exception as exc:
                _mark(email_delivery, EmergencyNotificationDelivery.STATUS_FAILED, str(exc))
                failed += 1
                errors.append(exc)

    sms_recipients = [
        value.strip()
        for value in getattr(settings, "SECUREHUB_EMERGENCY_SMS_RECIPIENTS", "").split(",")
        if value.strip()
    ]
    for recipient in sms_recipients:
        delivery = _create_delivery(
            emergency,
            channel="sms",
            provider=getattr(settings, "SECUREHUB_EMERGENCY_SMS_PROVIDER", "webhook"),
            recipient=recipient,
        )
        try:
            _send_sms(recipient, _sms_message(emergency))
            _mark(delivery, EmergencyNotificationDelivery.STATUS_SENT)
            sent += 1
        except RuntimeError as exc:
            _mark(delivery, EmergencyNotificationDelivery.STATUS_SKIPPED, str(exc))
            skipped += 1
        except Exception as exc:
            _mark(delivery, EmergencyNotificationDelivery.STATUS_FAILED, str(exc))
            failed += 1
            errors.append(exc)

    if errors:
        raise self.retry(exc=RuntimeError(f"{len(errors)} emergency notification(s) failed"))

    return {"emergency_id": emergency_id, "sent": sent, "failed": failed, "skipped": skipped}


def _body_for(emergency):
    site = emergency.site.name if emergency.site else "Away from site"
    return f"{emergency.customer.get_username()} requested patrol support at {site}."


def _email_message(emergency):
    maps_url = f"https://www.google.com/maps/search/?api=1&query={emergency.latitude},{emergency.longitude}"
    lines = [
        "Emergency patrol support requested.",
        "",
        f"Customer: {emergency.customer.get_full_name() or emergency.customer.get_username()}",
        f"Site: {emergency.site.name if emergency.site else 'Away from site'}",
        f"Phone: {emergency.contact_phone or 'Not provided'}",
        f"Location: {emergency.latitude}, {emergency.longitude}",
        f"Accuracy: {emergency.accuracy_m or 'unknown'} m",
        f"Map: {maps_url}",
        f"Request ID: {emergency.id}",
    ]
    if emergency.note:
        lines += ["", f"Note: {emergency.note}"]
    return "\n".join(lines)


def _sms_message(emergency):
    return (
        "SecureHub emergency: "
        f"{emergency.customer.get_username()} at {emergency.latitude},{emergency.longitude}. "
        f"ID {emergency.id}"
    )


def _send_sms(recipient: str, message: str) -> None:
    provider = getattr(settings, "SECUREHUB_EMERGENCY_SMS_PROVIDER", "hubtel").lower()
    if provider == "webhook":
        _send_sms_webhook(recipient, message)
        return
    _send_hubtel_sms(recipient, message)


def _send_hubtel_sms(recipient: str, message: str) -> None:
    from apps.communication.tasks import _normalize_phone

    client_id = settings.HUBTEL_CLIENT_ID
    client_secret = settings.HUBTEL_CLIENT_SECRET
    sender_name = settings.HUBTEL_SENDER_NAME or "SecureHub"
    if not client_id or not client_secret:
        raise RuntimeError("Hubtel credentials are not configured")

    phone = _normalize_phone(recipient)
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    response = requests.post(
        "https://sms.hubtel.com/v1/messages/send",
        json={"From": sender_name, "To": phone, "Content": message},
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    try:
        data = response.json()
    except Exception:
        data = {}
    if response.status_code not in (200, 201) and not data.get("messageId") and not (data.get("rate", 0) > 0):
        raise RuntimeError(f"Hubtel returned HTTP {response.status_code}: {response.text[:200]}")


def _send_sms_webhook(recipient: str, message: str) -> None:
    url = getattr(settings, "SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL", "")
    if not url:
        raise RuntimeError("SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL is not configured")
    payload = json.dumps({"to": recipient, "message": message}).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        if response.status >= 400:
            raise RuntimeError(f"SMS webhook returned HTTP {response.status}")
