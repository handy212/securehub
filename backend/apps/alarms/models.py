import uuid

from django.conf import settings
from django.db import models

from apps.sites.models import Site, Subsystem, Zone


class AlarmEvent(models.Model):
    # ---- Category choices ------------------------------------------------
    CATEGORY_ALARM = "alarm"
    CATEGORY_ARM = "arm"
    CATEGORY_SYSTEM = "system"
    CATEGORY_HEALTH = "health"
    CATEGORY_INFO = "info"
    CATEGORY_CHOICES = (
        (CATEGORY_ALARM, "Alarm"),
        (CATEGORY_ARM, "Arm/Disarm"),
        (CATEGORY_SYSTEM, "System"),
        (CATEGORY_HEALTH, "Health"),
        (CATEGORY_INFO, "Info"),
    )

    # ---- Severity choices ------------------------------------------------
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    SEVERITY_CHOICES = (
        (SEVERITY_CRITICAL, "Critical"),
        (SEVERITY_HIGH, "High"),
        (SEVERITY_MEDIUM, "Medium"),
        (SEVERITY_LOW, "Low"),
    )

    # ---- Core fields -----------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="events")
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    # ---- Classification --------------------------------------------------
    event_type = models.CharField(max_length=64)
    event_category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_INFO,
        db_index=True,
    )
    severity = models.CharField(
        max_length=16,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_LOW,
        db_index=True,
    )

    # ---- Deduplication ---------------------------------------------------
    # sha256 hash — unique per site to prevent MQ replay duplicates.
    source_event_id = models.CharField(max_length=128, blank=True, db_index=True)

    # ---- Extracted key fields (avoids full payload scan on queries) -------
    device_serial = models.CharField(max_length=64, blank=True, db_index=True)
    event_code = models.CharField(max_length=64, blank=True)
    performed_by = models.CharField(max_length=128, blank=True, db_index=True, verbose_name="User")

    # ---- Raw payload (preserved for audit / debugging) -------------------
    payload = models.JSONField(default=dict)

    # ---- Acknowledgement -------------------------------------------------
    acknowledged = models.BooleanField(default=False, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acknowledged_events",
    )

    # ---- Timestamps ------------------------------------------------------
    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at",)
        indexes = [
            # Fast timeline queries per site
            models.Index(fields=["site", "-occurred_at"], name="alarm_event_site_time_idx"),
            # Composite dedup lookup (site + hash)
            models.Index(fields=["site", "source_event_id"], name="alarm_event_site_hash_idx"),
            # Filter by type (used in status dashboards)
            models.Index(fields=["event_type"], name="alarm_event_type_idx"),
        ]
        constraints = [
            # Prevent duplicate MQ events from being persisted under race conditions.
            # The constraint only fires when source_event_id is non-empty.
            models.UniqueConstraint(
                fields=["site", "source_event_id"],
                condition=models.Q(source_event_id__gt=""),
                name="unique_event_per_site",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.site} [{self.severity}]"


class ArmDisarmCommand(models.Model):
    ACTION_ARM = "arm"
    ACTION_DISARM = "disarm"
    ACTION_STAY_ARM = "stay-arm"
    ACTION_CLEAR_ALARM = "clear-alarm"
    ACTION_CHOICES = (
        (ACTION_ARM, "Arm"),
        (ACTION_DISARM, "Disarm"),
        (ACTION_STAY_ARM, "Stay Arm"),
        (ACTION_CLEAR_ALARM, "Clear Alarm"),
    )

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="commands")
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.CASCADE,
        related_name="commands",
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # ---- Device ------------------------------------------------------
    # Serial of the panel that received the command, for audit purposes.
    device_serial = models.CharField(max_length=64, blank=True)

    # ---- Payloads ----------------------------------------------------
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)

    # ---- Timestamps --------------------------------------------------
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            # Prevent duplicate commands from double-taps / retried API calls.
            models.UniqueConstraint(
                fields=["site", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="unique_command_per_site",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.subsystem} [{self.status}]"


class NotificationDelivery(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        AlarmEvent,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    channel = models.CharField(max_length=32)       # e.g. "push", "sms", "whatsapp"
    provider = models.CharField(max_length=32, blank=True)  # e.g. "firebase", "twilio"
    recipient = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)

    # ---- Retry tracking ----------------------------------------------
    retry_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.channel}/{self.provider} → {self.recipient} [{self.status}]"
