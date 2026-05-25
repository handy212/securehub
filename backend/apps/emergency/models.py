import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.sites.models import Site


class EmergencyServicePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monthly_rate", "name"]

    def __str__(self) -> str:
        return f"{self.name} - GHc {self.monthly_rate}/mo"


class EmergencyServiceStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    OVERDUE = "overdue", "Overdue"
    SUSPENDED = "suspended", "Suspended"
    CANCELLED = "cancelled", "Cancelled"


class AccountEmergencyService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_service",
    )
    plan = models.ForeignKey(
        EmergencyServicePlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_services",
    )
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=16,
        choices=EmergencyServiceStatus.choices,
        default=EmergencyServiceStatus.ACTIVE,
        db_index=True,
    )
    next_due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self) -> bool:
        return self.status in (EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE)

    def __str__(self) -> str:
        return f"{self.user} emergency service - {self.status}"


class SiteEmergencyService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="emergency_service",
    )
    plan = models.ForeignKey(
        EmergencyServicePlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_services",
    )
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=16,
        choices=EmergencyServiceStatus.choices,
        default=EmergencyServiceStatus.ACTIVE,
        db_index=True,
    )
    next_due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self) -> bool:
        return self.status in (EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE)

    def __str__(self) -> str:
        return f"{self.site} emergency service - {self.status}"


class EmergencyRequest(models.Model):
    STATUS_OPEN = "open"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_DISPATCHED = "dispatched"
    STATUS_ARRIVED = "arrived"
    STATUS_RESOLVED = "resolved"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_ARRIVED, "Arrived"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CANCELLED, "Cancelled"),
    )
    ACTIVE_STATUSES = {
        STATUS_OPEN,
        STATUS_ACKNOWLEDGED,
        STATUS_DISPATCHED,
        STATUS_ARRIVED,
    }

    CONTEXT_ON_SITE = "on_site"
    CONTEXT_AWAY = "away"
    CONTEXT_UNKNOWN = "unknown"
    CONTEXT_CHOICES = (
        (CONTEXT_ON_SITE, "On site"),
        (CONTEXT_AWAY, "Away from site"),
        (CONTEXT_UNKNOWN, "Unknown"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_requests",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_requests",
    )
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    trigger_context = models.CharField(
        max_length=16,
        choices=CONTEXT_CHOICES,
        default=CONTEXT_UNKNOWN,
    )
    latitude = models.DecimalField(max_digits=12, decimal_places=9)
    longitude = models.DecimalField(max_digits=12, decimal_places=9)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    altitude_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed_mps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    heading_deg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    device_timestamp = models.DateTimeField(null=True, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_emergency_requests",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    assignment_note = models.CharField(max_length=255, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_emergency_requests",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatched_emergency_requests",
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_emergency_requests",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="emergency_status_time_idx"),
            models.Index(fields=["customer", "-created_at"], name="emergency_customer_time_idx"),
            models.Index(fields=["site", "-created_at"], name="emergency_site_time_idx"),
        ]

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES

    def assign(self, user, *, actor=None, note: str = "") -> None:
        self.assigned_to = user
        self.assigned_at = timezone.now()
        self.assignment_note = note
        update_fields = ["assigned_to", "assigned_at", "assignment_note", "updated_at"]
        if self.status == self.STATUS_OPEN:
            self.status = self.STATUS_ACKNOWLEDGED
            self.acknowledged_by = actor
            self.acknowledged_at = self.assigned_at
            update_fields += ["status", "acknowledged_by", "acknowledged_at"]
        self.save(update_fields=update_fields)

    def transition(self, status: str, *, actor=None, reason: str = "") -> None:
        now = timezone.now()
        self.status = status
        update_fields = ["status", "updated_at"]
        if status == self.STATUS_ACKNOWLEDGED:
            self.acknowledged_by = actor
            self.acknowledged_at = now
            update_fields += ["acknowledged_by", "acknowledged_at"]
        elif status == self.STATUS_DISPATCHED:
            self.dispatched_by = actor
            self.dispatched_at = now
            update_fields += ["dispatched_by", "dispatched_at"]
        elif status == self.STATUS_ARRIVED:
            self.arrived_at = now
            update_fields.append("arrived_at")
        elif status == self.STATUS_RESOLVED:
            self.resolved_by = actor
            self.resolved_at = now
            update_fields += ["resolved_by", "resolved_at"]
        elif status == self.STATUS_CANCELLED:
            self.cancelled_at = now
            self.cancellation_reason = reason
            update_fields += ["cancelled_at", "cancellation_reason"]
        self.save(update_fields=update_fields)
        if status == self.STATUS_DISPATCHED:
            from apps.guarding.dispatch_bridge import create_dispatch_from_emergency

            create_dispatch_from_emergency(self, actor=actor)

    def __str__(self) -> str:
        return f"Emergency {self.id} - {self.customer} - {self.status}"


class EmergencyLocationUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emergency_request = models.ForeignKey(
        EmergencyRequest,
        on_delete=models.CASCADE,
        related_name="location_updates",
    )
    latitude = models.DecimalField(max_digits=12, decimal_places=9)
    longitude = models.DecimalField(max_digits=12, decimal_places=9)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    altitude_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed_mps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    heading_deg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    device_timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class EmergencyNotificationDelivery(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emergency_request = models.ForeignKey(
        EmergencyRequest,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    channel = models.CharField(max_length=32)
    provider = models.CharField(max_length=32, blank=True)
    recipient = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
