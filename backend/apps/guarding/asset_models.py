"""Guard asset catalog, stock, post kits, and shift custody manifests."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.sites.models import Site

from .models import GuardPost, ShiftAssignment, _validate_status_transition


class GuardAssetType(models.Model):
    class Category(models.TextChoices):
        RADIO = "radio", "Radio"
        KEYS = "keys", "Keys"
        UNIFORM = "uniform", "Uniform"
        WEAPON_ACCESSORY = "weapon_accessory", "Weapon accessory"
        VEHICLE = "vehicle", "Vehicle"
        OTHER = "other", "Other"

    class TrackingMode(models.TextChoices):
        SERIAL = "serial", "Serial"
        QUANTITY = "quantity", "Quantity"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=32, choices=Category.choices, default=Category.OTHER, db_index=True)
    tracking_mode = models.CharField(max_length=16, choices=TrackingMode.choices, default=TrackingMode.SERIAL)
    requires_return = models.BooleanField(default=True)
    default_condition_check = models.BooleanField(default=True)
    replacement_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class GuardAssetDepot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_asset_depots",
        help_text="Leave blank for central / organization-wide depot.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        if self.site_id:
            return f"{self.name} @ {self.site.name}"
        return self.name


class GuardAssetUnit(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ISSUED = "issued", "Issued"
        MAINTENANCE = "maintenance", "Maintenance"
        RETIRED = "retired", "Retired"
        LOST = "lost", "Lost"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_type = models.ForeignKey(GuardAssetType, on_delete=models.PROTECT, related_name="units")
    depot = models.ForeignKey(GuardAssetDepot, on_delete=models.PROTECT, related_name="units")
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_asset_units",
        help_text="Optional restriction: unit only issuable for this site.",
    )
    asset_tag = models.CharField(max_length=80, unique=True, db_index=True)
    serial_number = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_tag"]
        indexes = [
            models.Index(fields=["asset_type", "status"], name="guard_asset_unit_type_st_idx"),
        ]

    def __str__(self) -> str:
        return self.asset_tag


class GuardAssetStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_type = models.ForeignKey(GuardAssetType, on_delete=models.PROTECT, related_name="stock_levels")
    depot = models.ForeignKey(GuardAssetDepot, on_delete=models.PROTECT, related_name="stock_levels")
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["depot__name", "asset_type__name"]
        unique_together = ("asset_type", "depot")

    def __str__(self) -> str:
        return f"{self.asset_type.code} @ {self.depot.name}: {self.quantity_on_hand}"

    @property
    def quantity_available(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)


class GuardAssetMaintenanceLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(GuardAssetUnit, on_delete=models.CASCADE, related_name="maintenance_logs")
    status_before = models.CharField(max_length=24, blank=True)
    status_after = models.CharField(max_length=24, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_asset_maintenance_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Maintenance {self.unit.asset_tag}"


class GuardingAssetPolicy(models.Model):
    class EnforcementMode(models.TextChoices):
        ADVISORY = "advisory", "Advisory"
        STRICT = "strict", "Strict"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="guarding_asset_policy",
    )
    post = models.OneToOneField(
        GuardPost,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asset_policy",
    )
    is_active = models.BooleanField(default=True)
    default_mode = models.CharField(
        max_length=16,
        choices=EnforcementMode.choices,
        default=EnforcementMode.ADVISORY,
    )
    enforce_issue_before_clock_in = models.BooleanField(default=True)
    enforce_return_before_clock_out = models.BooleanField(default=True)
    allow_supervisor_override = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Guarding asset policies"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(site__isnull=False, post__isnull=True)
                    | models.Q(site__isnull=True, post__isnull=False)
                ),
                name="guard_asset_policy_site_xor_post",
            ),
        ]

    def clean(self):
        if self.site_id and self.post_id:
            raise ValidationError("Policy must be attached to either a site or a post, not both.")
        if not self.site_id and not self.post_id:
            raise ValidationError("Policy must be attached to a site or a post.")

    def __str__(self) -> str:
        if self.post_id:
            return f"Asset policy — {self.post}"
        return f"Asset policy — {self.site}"


class PostAssetKit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GuardPost, on_delete=models.CASCADE, related_name="asset_kits")
    name = models.CharField(max_length=160)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["post__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.post})"


class PostAssetKitLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(PostAssetKit, on_delete=models.CASCADE, related_name="lines")
    asset_type = models.ForeignKey(GuardAssetType, on_delete=models.PROTECT, related_name="kit_lines")
    quantity_required = models.PositiveSmallIntegerField(default=1)
    is_optional = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kit", "asset_type__name"]
        unique_together = ("kit", "asset_type")

    def __str__(self) -> str:
        return f"{self.kit}: {self.asset_type.code} x{self.quantity_required}"


class ShiftAssetManifest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PARTIAL_RETURN = "partial_return", "Partial return"
        CLOSED = "closed", "Closed"
        EXCEPTION = "exception", "Exception"

    class EnforcementMode(models.TextChoices):
        ADVISORY = "advisory", "Advisory"
        STRICT = "strict", "Strict"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.OneToOneField(
        ShiftAssignment,
        on_delete=models.CASCADE,
        related_name="asset_manifest",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    enforcement_mode = models.CharField(
        max_length=16,
        choices=EnforcementMode.choices,
        default=EnforcementMode.ADVISORY,
    )
    depot = models.ForeignKey(
        GuardAssetDepot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifests",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_shift_asset_manifests",
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_shift_asset_manifests",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    guard_confirmed_at = models.DateTimeField(null=True, blank=True)
    override_clock_in = models.BooleanField(default=False)
    override_clock_out = models.BooleanField(default=False)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overridden_shift_asset_manifests",
    )
    override_at = models.DateTimeField(null=True, blank=True)
    override_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Manifest {self.assignment_id} ({self.status})"

    def clean(self):
        allowed = {
            self.Status.DRAFT: {self.Status.ISSUED, self.Status.EXCEPTION},
            self.Status.ISSUED: {self.Status.PARTIAL_RETURN, self.Status.CLOSED, self.Status.EXCEPTION},
            self.Status.PARTIAL_RETURN: {self.Status.CLOSED, self.Status.EXCEPTION},
            self.Status.CLOSED: set(),
            self.Status.EXCEPTION: {self.Status.CLOSED},
        }
        _validate_status_transition(self, allowed, label="Shift asset manifest")


class ShiftAssetManifestLine(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ISSUED = "issued", "Issued"
        RETURNED = "returned", "Returned"
        LOST = "lost", "Lost"
        DAMAGED = "damaged", "Damaged"
        NOT_REQUIRED = "not_required", "Not required"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey(ShiftAssetManifest, on_delete=models.CASCADE, related_name="lines")
    asset_type = models.ForeignKey(GuardAssetType, on_delete=models.PROTECT, related_name="manifest_lines")
    asset_unit = models.ForeignKey(
        GuardAssetUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifest_lines",
    )
    expected_qty = models.PositiveSmallIntegerField(default=1)
    issued_qty = models.PositiveSmallIntegerField(default=0)
    returned_qty = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    condition_out = models.CharField(max_length=120, blank=True)
    condition_in = models.CharField(max_length=120, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["manifest", "asset_type__name"]

    def __str__(self) -> str:
        return f"{self.asset_type.code} ({self.status})"
