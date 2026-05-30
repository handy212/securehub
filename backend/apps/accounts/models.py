import uuid

from django.conf import settings
from django.db import models

from apps.accounts.rbac import OperatorRole


class CustomerGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#6366f1")
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    phone_number = models.CharField(max_length=32, blank=True)
    is_mobile_user = models.BooleanField(default=True)
    group = models.ForeignKey(
        "CustomerGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    google_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.user.get_username()


class StaffOperatorProfile(models.Model):
    """Role-based access for operator console staff (is_staff users)."""

    Role = OperatorRole

    @staticmethod
    def default_role_for_user(user) -> str:
        from .rbac import default_role_for_user

        return default_role_for_user(is_superuser=bool(getattr(user, "is_superuser", False)))

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="operator_profile",
    )
    role = models.CharField(
        max_length=32,
        choices=OperatorRole.CHOICES,
        default=OperatorRole.OPERATIONS,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "staff operator profile"
        verbose_name_plural = "staff operator profiles"

    def __str__(self) -> str:
        return f"{self.user.get_username()} ({self.get_role_display()})"


class FCMDevice(models.Model):
    PLATFORM_ANDROID = "android"
    PLATFORM_IOS = "ios"
    PLATFORM_CHOICES = (
        (PLATFORM_ANDROID, "Android"),
        (PLATFORM_IOS, "iOS"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_devices",
    )
    token = models.TextField(unique=True)
    platform = models.CharField(
        max_length=16, choices=PLATFORM_CHOICES, default=PLATFORM_ANDROID
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user.get_username()} / {self.platform}"
