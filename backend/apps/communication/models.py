import uuid
from django.conf import settings
from django.db import models

class BroadcastMessage(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    TYPE_GENERAL = "general"
    TYPE_BILLING = "billing"
    TYPE_ALERT = "alert"
    TYPE_CHOICES = (
        (TYPE_GENERAL, "General"),
        (TYPE_BILLING, "Billing Notice"),
        (TYPE_ALERT, "System Alert"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField()
    message_type = models.CharField(
        max_length=16,
        choices=TYPE_CHOICES,
        default=TYPE_GENERAL,
    )
    # Delivery channels
    send_push = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)

    # Targeting: recipient → single user, recipient_group → group, both null → all mobile users
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="broadcast_messages",
    )
    recipient_group = models.ForeignKey(
        "accounts.CustomerGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="broadcast_messages",
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_broadcasts",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    push_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.title} — {self.status}"


class BroadcastMessageView(models.Model):
    message = models.ForeignKey(
        BroadcastMessage,
        on_delete=models.CASCADE,
        related_name="views",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viewed_broadcasts",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user")]
        ordering = ["-viewed_at"]

    def __str__(self) -> str:
        return f"{self.user.username} viewed {self.message.title}"
