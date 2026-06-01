import logging
import tempfile
import uuid
import zlib
from contextlib import contextmanager
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.alarms.event_labels import humanize_event_label

logger = logging.getLogger(__name__)


@contextmanager
def _non_overlapping_task_lock(lock_name: str):
    """
    Use a Postgres advisory lock to keep slow polling tasks from stacking up.
    SQLite/dev uses a filesystem lock so multi-process workers do not collide
    on the single-writer database.
    """
    if connection.vendor != "postgresql":
        try:
            import fcntl
        except ImportError:
            yield True
            return

        lock_id = zlib.crc32(lock_name.encode("utf-8"))
        lock_path = Path(tempfile.gettempdir()) / f"securehub-task-{lock_id}.lock"
        lock_file = lock_path.open("w")
        acquired = False
        try:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                acquired = False
            yield acquired
        finally:
            if acquired:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
        return

    lock_id = zlib.crc32(lock_name.encode("utf-8"))
    acquired = False
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock_id])
        acquired = bool(cursor.fetchone()[0])

    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_id])


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def poll_mq_events(self) -> dict:
    """
    Long-poll Hik-Partner Pro MQ for alarm/device events.
    Per §3.34: the platform blocks up to 20 s when no events are pending.
    Schedule via Celery beat every 25 s so the call returns before the next
    invocation and the 2-hour platform cache window is never missed.

    Flow: poll_messages → process each message → confirm_messages (§3.35).
    """
    from apps.hik_adapter.client import HikPartnerClient
    from apps.hik_adapter.services import HikPartnerService

    if settings.CELERY_TASK_ALWAYS_EAGER:
        logger.warning(
            "poll_mq_events: skipped because CELERY_TASK_ALWAYS_EAGER=True. "
            "In eager mode, Celery beat executes tasks inline instead of queueing them. "
            "Run a worker with eager mode disabled for MQ polling."
        )
        return {"skipped": True, "reason": "celery eager mode"}

    client = HikPartnerClient()
    if not client.is_configured() or client.dry_run:
        return {"skipped": True, "reason": "not configured or dry_run"}
    if settings.HIK_PARTNER.get("DELIVERY_MODE", "mq") != "mq":
        return {"skipped": True, "reason": "delivery mode disabled polling"}

    try:
        result = client.poll_messages()
    except Exception as exc:
        logger.error("poll_mq_events: poll_messages failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)

    data = result.get("data", {})
    batch_id = data.get("batchId", "")
    messages = data.get("list", [])

    if not messages:
        logger.debug("poll_mq_events: MQ heartbeat — no messages (batch=%s)", batch_id)
        return {"processed": 0, "batch_id": batch_id}

    task_id = self.request.id or str(uuid.uuid4())[:8]
    logger.info("MQ[%s] processing batch %s (%d messages)", task_id, batch_id, len(messages))

    service = HikPartnerService()
    processed = failed = 0

    for msg in messages:
        try:
            event = service.process_mq_message(msg, source="mq_poll")
            if event is not None:
                processed += 1
            else:
                logger.debug("MQ[%s] skipped (no event created for %s)", task_id, msg.get("deviceSerial", "?"))
        except Exception as exc:
            logger.error(
                "MQ[%s] failed to process message serial=%s: %s",
                task_id, msg.get("deviceSerial", "?"), exc,
                exc_info=True,
            )
            failed += 1

    if failed:
        logger.warning(
            "MQ[%s] leaving batch %s unacknowledged after %d processing failure(s)",
            task_id,
            batch_id,
            failed,
        )
        raise self.retry(
            exc=RuntimeError(f"{failed} MQ message(s) failed"),
            countdown=5,
        )

    if batch_id:
        try:
            client.confirm_messages(batch_id)
        except Exception as exc:
            logger.error(
                "MQ[%s] confirm_messages failed for batch %s: %s",
                task_id, batch_id, exc,
                exc_info=True,
            )
            raise self.retry(exc=exc, countdown=5)

    logger.info("MQ[%s] batch complete: processed=%d failed=%d", task_id, processed, failed)
    return {"processed": processed, "failed": failed, "batch_id": batch_id}


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_webhook_messages(self, messages: list) -> dict:
    """
    Process a batch of webhook messages asynchronously.
    Called by HikWebhookView.post() so the HTTP response is returned
    immediately (< 1 s) and Hik-Partner Pro does not retry the delivery.

    Mirrors the per-message loop in poll_mq_events but does NOT confirm
    a batch_id (webhook delivery is fire-and-forget on the platform side).
    """
    from apps.hik_adapter.services import HikPartnerService

    task_id = self.request.id or str(uuid.uuid4())[:8]
    service = HikPartnerService()
    processed = failed = 0

    logger.info("WEBHOOK[%s] processing %d message(s)", task_id, len(messages))

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        try:
            # Notification is now handled within HikPartnerService.process_mq_message
            event = service.process_mq_message(msg, source="webhook")
            if event is not None:
                processed += 1
            else:
                logger.debug(
                    "process_webhook: message serial=%s skipped (no event created)",
                    msg.get("deviceSerial", "?"),
                )
        except Exception as exc:
            logger.error(
                "WEBHOOK[%s] failed to process message serial=%s: %s",
                task_id, msg.get("deviceSerial", "?"), exc,
                exc_info=True,
            )
            failed += 1

    logger.info(
        "WEBHOOK[%s] batch done: processed=%d failed=%d",
        task_id, processed, failed,
    )
    return {"task_id": task_id, "processed": processed, "failed": failed}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_alarm_notifications(self, event_id: str) -> dict:
    """
    Dispatch notifications for a single AlarmEvent to every user
    who has access to the event's site.

    Priority routing:
      - critical / high  → email + FCM
      - medium           → FCM only
      - low / info       → FCM only (skips email)
      - INFO category    → skipped entirely (Snapshots, heartbeats)

    Retries up to 3 times (60 s apart) on transient failures.
    The retry fires AFTER the full delivery loop so already-sent
    notifications are never duplicated on retry.
    """
    from apps.alarms.models import AlarmEvent, NotificationDelivery
    from apps.sites.models import CustomerSiteAccess

    try:
        event = AlarmEvent.objects.select_related(
            "site", "subsystem", "zone"
        ).get(id=event_id)
    except AlarmEvent.DoesNotExist:
        logger.warning("dispatch_alarm_notifications: event %s not found", event_id)
        return {"skipped": True, "reason": "event not found"}

    # Relaxed filtering: allow push notifications for most events. 
    # High-noise internal heartbeats/snapshots can still be handled via separate flags if needed.
    # if event.event_category == AlarmEvent.CATEGORY_INFO:
    #     logger.debug(...)
    #     return ...

    # Determine which channels to use based on severity
    high_priority = event.severity in (AlarmEvent.SEVERITY_CRITICAL, AlarmEvent.SEVERITY_HIGH)

    access_list = list(
        CustomerSiteAccess.objects.filter(site=event.site).select_related("user")
    )

    delivery_errors = []  # collect failures; retry once outside the loop
    sent = failed = 0

    for access in access_list:
        user = access.user
        recipient = user.email or user.username

        # Only send email for high-priority events to avoid inbox noise
        if high_priority and user.email:
            channel = "email"
        else:
            channel = "log"

        # Idempotency guard — skip if this channel already succeeded for this recipient.
        if NotificationDelivery.objects.filter(
            event=event,
            recipient=recipient,
            channel=channel,
            status=NotificationDelivery.STATUS_SENT,
        ).exists():
            logger.debug(
                "dispatch_alarm_notifications: skipping duplicate %s delivery to %s",
                channel,
                recipient,
            )
            continue

        delivery = _get_or_create_notification_delivery(
            event=event,
            channel=channel,
            recipient=recipient,
        )

        try:
            _deliver(delivery, event)
            delivery.status = NotificationDelivery.STATUS_SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ""
            delivery.save(update_fields=["status", "sent_at", "last_error"])
            sent += 1
        except Exception as exc:
            logger.error(
                "Notification delivery %s failed for %s: %s",
                delivery.id, recipient, exc,
                exc_info=True,
            )
            delivery.status = NotificationDelivery.STATUS_FAILED
            delivery.retry_count = self.request.retries
            delivery.last_error = str(exc)
            delivery.save(update_fields=["status", "retry_count", "last_error"])
            failed += 1
            delivery_errors.append((recipient, exc))

    # Push notifications (FCM) — always sent regardless of email routing
    fcm_sent = 0
    for access in access_list:
        recipient = access.user.email or access.user.username
        if NotificationDelivery.objects.filter(
            event=event,
            recipient=recipient,
            channel="push",
            provider="firebase",
            status=NotificationDelivery.STATUS_SENT,
        ).exists():
            logger.debug(
                "dispatch_alarm_notifications: skipping duplicate push delivery to %s",
                recipient,
            )
            continue

        delivery = _get_or_create_notification_delivery(
            event=event,
            channel="push",
            recipient=recipient,
            provider="firebase",
        )
        try:
            fcm_sent += _send_fcm_notification(access.user, event)
            delivery.status = NotificationDelivery.STATUS_SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ""
            delivery.save(update_fields=["status", "sent_at", "last_error"])
        except Exception as exc:
            delivery.status = NotificationDelivery.STATUS_FAILED
            delivery.retry_count = self.request.retries
            delivery.last_error = str(exc)
            delivery.save(update_fields=["status", "retry_count", "last_error"])
            logger.error(
                "FCM dispatch failed for user %s: %s", access.user.username, exc
            )

    logger.info(
        "Notifications for event %s: sent=%d failed=%d fcm_sent=%d",
        event_id, sent, failed, fcm_sent,
    )

    # Retry AFTER the full loop so successful deliveries are never duplicated.
    # The duplicate guard above will skip already-sent recipients on retry.
    if delivery_errors:
        raise self.retry(
            exc=Exception(f"{len(delivery_errors)} notification(s) failed"),
        )

    return {"event_id": event_id, "sent": sent, "failed": failed, "fcm_sent": fcm_sent}


@shared_task(bind=True, max_retries=3)
def fetch_alarm_image_url(self, event_id: str) -> dict:
    """
    Fetch a time-limited viewable URL for a Hikvision alarm image attachment.
    The MQ/Webhook payload contains internal 'ISAPI_FILES/...' paths; this task
    exchanges them for real 'https://...' links via the /v1/alarm/pictureurl API.
    """
    from apps.alarms.models import AlarmEvent
    from apps.hik_adapter.client import HikPartnerClient

    try:
        event = AlarmEvent.objects.get(id=event_id)
    except AlarmEvent.DoesNotExist:
        return {"skipped": True, "reason": "event not found"}

    pictures = event.payload.get("pictures", [])
    if not pictures:
        return {"skipped": True, "reason": "no pictures to fetch"}

    client = HikPartnerClient()
    updated = False
    
    for pic in pictures:
        if pic.get("needs_url_fetch"):
            try:
                internal_path = pic.get("url")
                # Call Hikvision to get the real public URL (§3.36)
                result = client.get_alarm_picture_url(internal_path)
                real_url = result.get("pictureUrl")
                if real_url:
                    pic["url"] = real_url
                    pic["needs_url_fetch"] = False
                    updated = True
            except Exception as exc:
                logger.error("IMAGE_FETCH failed for event %s path=%s: %s", event_id, pic.get("url"), exc)

    if updated:
        event.payload["pictures"] = pictures
        event.save(update_fields=["payload"])
        return {"event_id": event_id, "updated": True}

    return {"event_id": event_id, "updated": False}


# ---------------------------------------------------------------------------
# Channel dispatchers
# ---------------------------------------------------------------------------

def _deliver(delivery, event) -> None:
    if delivery.channel == "email":
        _send_email(delivery, event)
    else:
        _log_notification(delivery, event)


def _get_or_create_notification_delivery(*, event, channel: str, recipient: str, provider: str = ""):
    delivery = (
        event.notification_deliveries.filter(
            channel=channel,
            recipient=recipient,
            provider=provider,
        )
        .order_by("-created_at")
        .first()
    )
    if delivery is None:
        delivery = event.notification_deliveries.create(
            channel=channel,
            recipient=recipient,
            provider=provider,
        )
    return delivery


def _send_email(delivery, event) -> None:
    from django.core.mail import send_mail
    from django.conf import settings

    display_name = (event.payload or {}).get("event_name") or humanize_event_label(event.event_type)
    subject = f"[SecureHub] {display_name} — {event.site.name}"

    lines = [
        f"Event   : {display_name}",
        f"Site    : {event.site.name}",
        f"Time    : {event.occurred_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]
    if event.subsystem:
        lines.append(f"Partition: {event.subsystem.name}")
    if event.zone:
        lines.append(f"Zone    : {event.zone.name} (state: {event.zone.state})")
    if event.performed_by:
        lines.append(f"User    : {event.performed_by}")

    send_mail(
        subject=subject,
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[delivery.recipient],
        fail_silently=False,
    )


def _log_notification(delivery, event) -> None:
    display_name = (event.payload or {}).get("event_name") or humanize_event_label(event.event_type)
    logger.info(
        "NOTIFICATION [log] → %s | event=%s site=%s occurred_at=%s",
        delivery.recipient,
        display_name,
        event.site.name,
        event.occurred_at.isoformat(),
    )


def _send_generic_fcm_notification(user, title: str, body: str, data: dict = None) -> int:
    """
    Core logic to send an FCM push notification to all active devices 
    registered for the user.
    """
    from apps.communication.push import send_push_to_user

    result = send_push_to_user(user, title=title, body=body, data=data or {})
    return result.get("sent", 0)


def _send_fcm_notification(user, event) -> int:
    """
    Legacy wrapper for AlarmEvent-based notifications.
    """
    display_name = (event.payload or {}).get("event_name") or humanize_event_label(event.event_type)
    title = f"[{event.site.name}] {display_name}"
    body_parts = []
    if event.subsystem:
        body_parts.append(event.subsystem.name)
    if event.zone:
        body_parts.append(event.zone.name)
    
    body = " — ".join(body_parts) if body_parts else event.occurred_at.strftime("%H:%M UTC")

    # If this is an arm/disarm/status event, emphasize the performer
    if event.performed_by:
        body = f"{body} — By {event.performed_by}"

    data = {
        "type": "alarm",
        "site_id": str(event.site.id),
        "event_id": str(event.id),
        "event_type": event.event_type,
        "event_name": display_name,
    }
    return _send_generic_fcm_notification(user, title, body, data)


# ---------------------------------------------------------------------------
# Subscription lifecycle tasks
# ---------------------------------------------------------------------------

@shared_task
def check_subscription_statuses() -> dict:
    """
    Daily task that:
    1. Marks subscriptions as 'overdue' when next_due_date has passed.
    2. Suspends subscriptions that have been overdue beyond their grace period.

    Run via Celery beat once per day.
    """
    from apps.sites.models import Subscription

    today = timezone.localdate()
    newly_overdue = newly_suspended = 0

    active_past_due = Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE,
        next_due_date__lt=today,
    )
    for sub in active_past_due:
        sub.status = Subscription.STATUS_OVERDUE
        sub.save(update_fields=["status", "updated_at"])
        newly_overdue += 1
        logger.info(
            "Subscription for site '%s' marked overdue (due %s)",
            sub.site.name,
            sub.next_due_date,
        )

    from datetime import timedelta
    overdue_subs = Subscription.objects.filter(status=Subscription.STATUS_OVERDUE)
    for sub in overdue_subs:
        grace_deadline = sub.next_due_date + timedelta(days=sub.grace_period_days)
        if today > grace_deadline:
            sub.suspend()
            newly_suspended += 1
            logger.warning(
                "Subscription for site '%s' SUSPENDED (overdue since %s, grace expired %s)",
                sub.site.name,
                sub.next_due_date,
                grace_deadline,
            )
            send_suspension_notice.delay(str(sub.id))

    return {"newly_overdue": newly_overdue, "newly_suspended": newly_suspended}


@shared_task
def send_payment_reminders() -> dict:
    """
    Daily task that sends a payment reminder email 3 days before the due date
    and again on the due date itself for active subscriptions.
    """
    from datetime import timedelta
    from apps.sites.models import Subscription, CustomerSiteAccess

    today = timezone.localdate()
    remind_dates = {today + timedelta(days=3), today}
    sent = 0

    for sub in Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE,
        next_due_date__in=remind_dates,
    ).select_related("site"):
        days_left = (sub.next_due_date - today).days
        label = "in 3 days" if days_left == 3 else "TODAY"

        access_list = CustomerSiteAccess.objects.filter(
            site=sub.site
        ).select_related("user")

        for access in access_list:
            user = access.user
            if not user.email:
                continue
            try:
                from django.core.mail import send_mail
                from django.conf import settings as conf
                send_mail(
                    subject=f"[SecureHub] Payment reminder — {sub.site.name}",
                    message=(
                        f"Hi {user.get_full_name() or user.username},\n\n"
                        f"Your monthly subscription for '{sub.site.name}' "
                        f"({sub.monthly_rate}) is due {label} ({sub.next_due_date}).\n\n"
                        f"Please ensure payment is made to avoid service interruption.\n\n"
                        f"— SecureHub"
                    ),
                    from_email=conf.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                sent += 1
            except Exception as exc:
                logger.error("Payment reminder send failed for %s: %s", user.email, exc)

    return {"reminders_sent": sent}


@shared_task
def poll_device_health() -> dict:
    """
    Periodically calls the Hik site/health/report API for every active site
    and updates AlarmPanelDevice and Zone health fields (battery, tamper, signal,
    online/work status).

    Runs every 5 minutes via Celery beat.
    """
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    with _non_overlapping_task_lock("poll_device_health") as acquired:
        if not acquired:
            logger.info("poll_device_health: previous run still active; skipping overlap")
            return {"skipped": True, "reason": "previous run still active"}

        service = HikPartnerService()
        if not service.client.is_configured() or service.client.dry_run:
            return {"skipped": True, "reason": "not configured or dry_run"}

        sites = Site.objects.filter(is_active=True).exclude(hik_site_id="")
        panels_total = zones_total = errors = 0

        for site in sites:
            try:
                result = service.refresh_site_health(site)
                panels_total += result.get("panels_updated", 0)
                zones_total += result.get("zones_updated", 0)
            except Exception as exc:
                logger.error(
                    "poll_device_health: failed for site %s: %s", site.name, exc, exc_info=True
                )
                errors += 1

        return {"panels_updated": panels_total, "zones_updated": zones_total, "errors": errors}


@shared_task
def sync_all_alarm_status() -> dict:
    """
    Periodically pull zone states (open/close/arm/alarm) from ISAPI for every
    active site. This keeps zone state current between MQ events and ensures
    signal/battery from ISAPI are populated on first run.

    Runs every 2 minutes via Celery beat.
    """
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    with _non_overlapping_task_lock("sync_all_alarm_status") as acquired:
        if not acquired:
            logger.info("sync_all_alarm_status: previous run still active; skipping overlap")
            return {"skipped": True, "reason": "previous run still active"}

        service = HikPartnerService()
        if not service.client.is_configured() or service.client.dry_run:
            return {"skipped": True, "reason": "not configured or dry_run"}

        sites = Site.objects.filter(is_active=True).exclude(hik_site_id="")
        errors = 0

        for site in sites:
            try:
                service.sync_alarm_status(site)
            except Exception as exc:
                logger.error(
                    "sync_all_alarm_status: failed for site %s: %s", site.name, exc, exc_info=True
                )
                errors += 1

        return {"sites_synced": sites.count() - errors, "errors": errors}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def initial_site_discovery(self, site_id: str) -> dict:
    """
    Run the slow Hik-Partner discovery workflow after a site is created.
    Keeping this out of the staff HTTP request avoids production timeouts while
    still filling metadata, location, devices, partitions, zones, and health.
    """
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    try:
        site = Site.objects.get(id=site_id)
    except Site.DoesNotExist:
        return {"skipped": True, "reason": "site not found"}

    service = HikPartnerService()
    if not service.client.is_configured() or service.client.dry_run:
        return {"skipped": True, "reason": "not configured or dry_run"}

    with _non_overlapping_task_lock(f"hik_site_sync:{site_id}") as acquired:
        if not acquired:
            logger.info("initial_site_discovery: sync already active for site %s; skipping overlap", site.name)
            return {"skipped": True, "reason": "site sync already active"}

        try:
            device_result = service.sync_site_devices(site)
            if site.latitude is None or site.longitude is None:
                service.geocode_site_location(site)
            service.sync_alarm_status(site)
            try:
                health_result = service.refresh_site_health(site)
            except Exception as health_exc:
                logger.warning(
                    "initial_site_discovery: health refresh failed for site %s: %s",
                    site.name,
                    health_exc,
                )
                health_result = {"health_warning": str(health_exc)}
        except Exception as exc:
            logger.error(
                "initial_site_discovery: failed for site %s: %s",
                site.name,
                exc,
                exc_info=True,
            )
            raise self.retry(exc=exc)

    return {
        "site_id": site_id,
        "devices_seen": device_result.get("devices_seen", 0),
        "synced_panels": device_result.get("synced_panels", 0),
        "panels_updated": health_result.get("panels_updated", 0),
        "zones_updated": health_result.get("zones_updated", 0),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_hik_site_devices(self, site_id: str) -> dict:
    """Synchronize Hik devices for one site outside the web request."""
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    try:
        site = Site.objects.get(id=site_id)
    except Site.DoesNotExist:
        return {"skipped": True, "reason": "site not found"}

    service = HikPartnerService()
    if not service.client.is_configured() or service.client.dry_run:
        return {"skipped": True, "reason": "not configured or dry_run"}

    with _non_overlapping_task_lock(f"hik_site_sync:{site_id}") as acquired:
        if not acquired:
            logger.info("sync_hik_site_devices: sync already active for site %s; skipping overlap", site.name)
            return {"skipped": True, "reason": "site sync already active"}

        try:
            return service.sync_site_devices(site)
        except Exception as exc:
            logger.error("sync_hik_site_devices: failed for site %s: %s", site.name, exc, exc_info=True)
            raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_hik_alarm_status(self, site_id: str) -> dict:
    """Synchronize partitions/zones plus health/peripheral data outside the web request."""
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    try:
        site = Site.objects.get(id=site_id)
    except Site.DoesNotExist:
        return {"skipped": True, "reason": "site not found"}

    service = HikPartnerService()
    if not service.client.is_configured() or service.client.dry_run:
        return {"skipped": True, "reason": "not configured or dry_run"}

    with _non_overlapping_task_lock(f"hik_site_sync:{site_id}") as acquired:
        if not acquired:
            logger.info("sync_hik_alarm_status: sync already active for site %s; skipping overlap", site.name)
            return {"skipped": True, "reason": "site sync already active"}

        try:
            device_result = service.sync_site_devices(site)
            service.sync_alarm_status(site)
            try:
                health_result = service.refresh_site_health(site)
            except Exception as health_exc:
                logger.warning(
                    "sync_hik_alarm_status: health refresh failed for site %s: %s",
                    site.name,
                    health_exc,
                )
                health_result = {"health_warning": str(health_exc)}
        except Exception as exc:
            logger.error("sync_hik_alarm_status: failed for site %s: %s", site.name, exc, exc_info=True)
            raise self.retry(exc=exc)

    return {
        "site_id": site_id,
        "devices_seen": device_result.get("devices_seen", 0),
        "synced_panels": device_result.get("synced_panels", 0),
        "panels_updated": health_result.get("panels_updated", 0),
        "zones_updated": health_result.get("zones_updated", 0),
        "peripherals_updated": health_result.get("peripherals_updated", 0),
        "outputs_updated": health_result.get("outputs_updated", 0),
        "skipped": health_result.get("skipped", False),
        "reason": health_result.get("reason", ""),
        "health_warning": health_result.get("health_warning", ""),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def refresh_hik_site_health(self, site_id: str) -> dict:
    """Refresh health/peripheral data for one site outside the web request."""
    from apps.hik_adapter.services import HikPartnerService
    from apps.sites.models import Site

    try:
        site = Site.objects.get(id=site_id)
    except Site.DoesNotExist:
        return {"skipped": True, "reason": "site not found"}

    service = HikPartnerService()
    if not service.client.is_configured() or service.client.dry_run:
        return {"skipped": True, "reason": "not configured or dry_run"}

    try:
        return service.refresh_site_health(site)
    except Exception as exc:
        logger.error("refresh_hik_site_health: failed for site %s: %s", site.name, exc, exc_info=True)
        raise self.retry(exc=exc)


def _subscription_access_recipients(subscription):
    from apps.sites.models import CustomerSiteAccess

    return CustomerSiteAccess.objects.filter(
        site=subscription.site
    ).select_related("user")


def _send_subscription_notice_to_user(user, *, subject, message, push_title=None, push_body=None, data=None) -> bool:
    delivered = False
    if user.email:
        from django.core.mail import send_mail
        from django.conf import settings as conf

        send_mail(
            subject=subject,
            message=message,
            from_email=conf.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        delivered = True
    if push_title and push_body:
        delivered = _send_generic_fcm_notification(user, push_title, push_body, data or {}) > 0 or delivered
    return delivered


@shared_task
def send_subscription_lockout_notice(subscription_id: str, notice_type: str = "suspended") -> dict:
    """
    Sends lockout/cancellation notices to all users linked to the site whose
    subscription is no longer accessible.
    """
    from apps.sites.models import Subscription

    try:
        sub = Subscription.objects.select_related("site").get(id=subscription_id)
    except Subscription.DoesNotExist:
        return {"skipped": True}

    if notice_type == "cancelled":
        subject = f"[SecureHub] Service cancelled — {sub.site.name}"
        reason_line = "has been cancelled by your service provider"
        push_title = f"Service Cancelled — {sub.site.name}"
        push_body = "Access has been restricted because this service plan was cancelled."
    else:
        notice_type = "suspended"
        subject = f"[SecureHub] Service suspended — {sub.site.name}"
        reason_line = (
            f"has been suspended because the monthly subscription payment "
            f"(due {sub.next_due_date}) was not received within the grace period"
        )
        push_title = f"Service Suspended — {sub.site.name}"
        push_body = "Access has been restricted due to an unpaid balance. Tap to contact support."

    sent = 0
    for access in _subscription_access_recipients(sub):
        user = access.user
        try:
            was_sent = _send_subscription_notice_to_user(
                user,
                subject=subject,
                message=(
                    f"Hi {user.get_full_name() or user.username},\n\n"
                    f"Access to '{sub.site.name}' {reason_line}.\n\n"
                    f"To restore access please contact support.\n\n"
                    f"— SecureHub"
                ),
                push_title=push_title,
                push_body=push_body,
                data={"type": "billing_lockout", "site_id": str(sub.site.id)},
            )
            if was_sent:
                sent += 1
        except Exception as exc:
            logger.error("%s notice failed for %s: %s", notice_type, user.email, exc)

    return {"subscription_id": subscription_id, "notice_type": notice_type, "notices_sent": sent}


@shared_task
def send_suspension_notice(subscription_id: str) -> dict:
    """
    Backward-compatible task name for suspension notices.
    """
    return send_subscription_lockout_notice(subscription_id, notice_type="suspended")


@shared_task
def send_reactivation_notice(subscription_id: str) -> dict:
    from apps.sites.models import Subscription

    try:
        sub = Subscription.objects.select_related("site").get(id=subscription_id)
    except Subscription.DoesNotExist:
        return {"skipped": True}

    sent = 0
    for access in _subscription_access_recipients(sub):
        user = access.user
        try:
            was_sent = _send_subscription_notice_to_user(
                user,
                subject=f"[SecureHub] Service restored — {sub.site.name}",
                message=(
                    f"Hi {user.get_full_name() or user.username},\n\n"
                    f"Access to '{sub.site.name}' has been restored. "
                    f"Your next due date is {sub.next_due_date}.\n\n"
                    f"— SecureHub"
                ),
                push_title=f"Service Restored — {sub.site.name}",
                push_body="Access has been restored. You can open SecureHub again.",
                data={"type": "billing", "site_id": str(sub.site.id)},
            )
            if was_sent:
                sent += 1
        except Exception as exc:
            logger.error("Reactivation notice failed for %s: %s", user.email, exc)

    return {"subscription_id": subscription_id, "notices_sent": sent}
