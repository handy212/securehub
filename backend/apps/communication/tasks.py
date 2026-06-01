import base64
import logging

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel helpers
# ---------------------------------------------------------------------------

def _target_devices(msg):
    from apps.communication.push import active_devices_for_broadcast

    return active_devices_for_broadcast(msg)


def _target_phones(msg):
    from apps.accounts.models import CustomerProfile
    qs = CustomerProfile.objects.exclude(phone_number="")
    if msg.recipient:
        qs = qs.filter(user=msg.recipient)
    elif msg.recipient_group_id:
        qs = qs.filter(group_id=msg.recipient_group_id)
    return list(qs.values_list("phone_number", flat=True))


def _target_emails(msg):
    User = get_user_model()
    qs = User.objects.exclude(email="")
    if msg.recipient:
        qs = qs.filter(pk=msg.recipient_id)
    elif msg.recipient_group_id:
        qs = qs.filter(customer_profile__group_id=msg.recipient_group_id)
    else:
        qs = qs.filter(customer_profile__is_mobile_user=True)
    return list(qs.values_list("email", flat=True))


def _dispatch_push(msg):
    from apps.communication.push import send_push_to_devices

    data = {"type": msg.message_type, "message_id": str(msg.id)}
    data.update(msg.push_data or {})
    return send_push_to_devices(
        _target_devices(msg),
        title=msg.title,
        body=msg.body,
        data=data,
    )


def _normalize_phone(phone: str, country_code: str = "233") -> str:
    """Normalize a phone number to E.164 format (e.g. +233246999414)."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone:
        return phone
    if phone.startswith("+"):
        return phone  # already E.164
    if phone.startswith("00"):
        return "+" + phone[2:]  # 00233... → +233...
    if phone.startswith(country_code):
        return "+" + phone  # 233246... → +233246...
    if phone.startswith("0"):
        return "+" + country_code + phone[1:]  # 0246... → +233246...
    return "+" + country_code + phone  # bare 9-digit → +233246...


def _dispatch_sms(msg):
    client_id = settings.HUBTEL_CLIENT_ID
    client_secret = settings.HUBTEL_CLIENT_SECRET
    sender_name = settings.HUBTEL_SENDER_NAME or "SecureHub"

    if not client_id or not client_secret:
        logger.warning("Hubtel credentials not configured — skipping SMS channel")
        return {"sent": 0, "failed": 0, "reason": "Hubtel not configured"}

    phones = [_normalize_phone(p) for p in _target_phones(msg) if p]
    phones = [p for p in phones if len(p) >= 10]  # drop obviously invalid numbers
    if not phones:
        return {"sent": 0, "failed": 0, "reason": "no valid phone numbers"}

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }

    sent = failed = 0
    for phone in phones:
        try:
            resp = requests.post(
                "https://sms.hubtel.com/v1/messages/send",
                json={"From": sender_name, "To": phone, "Content": msg.body},
                headers=headers,
                timeout=15,
            )
            try:
                data = resp.json()
            except Exception:
                data = {}
            # Hubtel can return 400 but still process the message (quirky API).
            # Treat as success if they assigned a messageId or the rate > 0.
            if resp.status_code in (200, 201) or data.get("messageId") or (data.get("rate", 0) > 0):
                sent += 1
                logger.info("Hubtel SMS queued to %s (status=%s)", phone, data.get("statusDescription", ""))
            else:
                failed += 1
                logger.error("Hubtel SMS %s → HTTP %s: %s", phone, resp.status_code, resp.text[:200])
        except Exception as exc:
            failed += 1
            logger.error("Hubtel SMS error for %s: %s", phone, exc)

    return {"sent": sent, "failed": failed}


def _dispatch_email(msg):
    emails = _target_emails(msg)
    if not emails:
        return {"sent": 0, "failed": 0, "reason": "no email addresses"}

    sent = failed = 0
    for email in emails:
        try:
            send_mail(
                subject=msg.title,
                message=msg.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            sent += 1
        except Exception as exc:
            failed += 1
            logger.error("Email error for %s: %s", email, exc)

    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Unified broadcast task
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_broadcast(self, message_id: str) -> dict:
    from apps.communication.models import BroadcastMessage

    try:
        msg = BroadcastMessage.objects.get(id=message_id)
    except BroadcastMessage.DoesNotExist:
        logger.error("send_broadcast: message %s not found", message_id)
        return {"skipped": True, "reason": "message not found"}

    results = {}
    any_sent = False
    retryable_error = None

    if msg.send_push:
        try:
            results["push"] = _dispatch_push(msg)
            if results["push"]["sent"] > 0:
                any_sent = True
        except Exception as exc:
            logger.error("Push channel error: %s", exc)
            retryable_error = exc
            results["push"] = {"sent": 0, "failed": 0, "error": str(exc)}

    if msg.send_sms:
        try:
            results["sms"] = _dispatch_sms(msg)
            if results["sms"]["sent"] > 0:
                any_sent = True
        except Exception as exc:
            logger.error("SMS channel error: %s", exc)
            results["sms"] = {"sent": 0, "failed": 0, "error": str(exc)}

    if msg.send_email:
        try:
            results["email"] = _dispatch_email(msg)
            if results["email"]["sent"] > 0:
                any_sent = True
        except Exception as exc:
            logger.error("Email channel error: %s", exc)
            results["email"] = {"sent": 0, "failed": 0, "error": str(exc)}

    if retryable_error and not any_sent:
        raise self.retry(exc=retryable_error)

    msg.status = BroadcastMessage.STATUS_SENT if any_sent else BroadcastMessage.STATUS_FAILED
    msg.sent_at = timezone.now()
    msg.save(update_fields=["status", "sent_at"])

    return {"message_id": message_id, **results}


# Backward-compat alias for any tasks queued before this refactor
send_broadcast_push_notifications = send_broadcast
