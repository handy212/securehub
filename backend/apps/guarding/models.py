import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.sites.models import Site


class GuardingEventLog(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Source(models.TextChoices):
        SYSTEM = "system", "System"
        CONSOLE = "console", "Console"
        MOBILE = "mobile", "Mobile"
        API = "api", "API"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=80, db_index=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.INFO, db_index=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.SYSTEM, db_index=True)
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    object_label = models.CharField(max_length=80, blank=True, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    unique_key = models.CharField(max_length=160, unique=True, blank=True, null=True)
    guard = models.ForeignKey(
        "GuardProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_events",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarding_workflow_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarding_workflow_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["severity", "-created_at"], name="guard_event_sev_time_idx"),
            models.Index(fields=["object_label", "object_id"], name="guard_event_object_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_severity_display()} - {self.title}"


def _validate_status_transition(instance, allowed: dict[str, set[str]], *, label: str) -> None:
    if not instance.pk:
        return
    current_status = type(instance).objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    if current_status and current_status != instance.status and instance.status not in allowed.get(current_status, set()):
        raise ValidationError({"status": f"{label} cannot move from {current_status} to {instance.status}."})


def _validate_initial_status(instance, allowed: set[str], *, label: str) -> None:
    if not instance.pk and instance.status not in allowed:
        raise ValidationError({"status": f"{label} must start as one of: {', '.join(sorted(allowed))}."})


class GuardApplicant(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        BACKGROUND_CHECK = "background_check", "Background Check"
        OFFERED = "offered", "Offered"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.APPLIED, db_index=True)
    source = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    background_check_status = models.CharField(max_length=64, blank=True)
    interview_notes = models.TextField(blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_guard_applicants",
    )
    hired_guard = models.OneToOneField(
        "GuardProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_application",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="guard_app_status_time_idx"),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        allowed = {
            self.Status.APPLIED: {self.Status.SCREENING, self.Status.REJECTED, self.Status.WITHDRAWN},
            self.Status.SCREENING: {
                self.Status.INTERVIEW,
                self.Status.BACKGROUND_CHECK,
                self.Status.REJECTED,
                self.Status.WITHDRAWN,
            },
            self.Status.INTERVIEW: {
                self.Status.BACKGROUND_CHECK,
                self.Status.OFFERED,
                self.Status.REJECTED,
                self.Status.WITHDRAWN,
            },
            self.Status.BACKGROUND_CHECK: {self.Status.OFFERED, self.Status.REJECTED, self.Status.WITHDRAWN},
            self.Status.OFFERED: {self.Status.REJECTED, self.Status.WITHDRAWN},
            self.Status.HIRED: set(),
            self.Status.REJECTED: set(),
            self.Status.WITHDRAWN: set(),
        }
        _validate_initial_status(self, {self.Status.APPLIED}, label="Applicant")
        _validate_status_transition(self, allowed, label="Applicant")

    def __str__(self) -> str:
        return self.full_name


class GuardProfile(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        INACTIVE = "inactive", "Inactive"
        TERMINATED = "terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_profile",
    )
    employee_number = models.CharField(max_length=64, unique=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    home_address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_guards",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["status", "last_name"], name="guard_status_name_idx"),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        allowed = {
            self.Status.ACTIVE: {self.Status.SUSPENDED, self.Status.INACTIVE, self.Status.TERMINATED},
            self.Status.SUSPENDED: {self.Status.ACTIVE, self.Status.INACTIVE, self.Status.TERMINATED},
            self.Status.INACTIVE: {self.Status.ACTIVE, self.Status.TERMINATED},
            self.Status.TERMINATED: set(),
        }
        _validate_status_transition(self, allowed, label="Guard")

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_number})"


class GuardCredential(models.Model):
    class CredentialType(models.TextChoices):
        LICENSE = "license", "License"
        CERTIFICATION = "certification", "Certification"
        TRAINING = "training", "Training"
        MEDICAL = "medical", "Medical"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guard = models.ForeignKey(GuardProfile, on_delete=models.CASCADE, related_name="credentials")
    credential_type = models.CharField(max_length=32, choices=CredentialType.choices)
    name = models.CharField(max_length=160)
    issuing_authority = models.CharField(max_length=160, blank=True)
    reference_number = models.CharField(max_length=120, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True, db_index=True)
    verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expires_on", "name"]
        indexes = [
            models.Index(fields=["credential_type", "expires_on"], name="guard_cred_type_exp_idx"),
        ]

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_on and self.expires_on < timezone.localdate())

    def __str__(self) -> str:
        return f"{self.guard} - {self.name}"


class GuardDocument(models.Model):
    class DocumentType(models.TextChoices):
        ID = "id", "ID"
        CONTRACT = "contract", "Contract"
        PERMIT = "permit", "Permit"
        REFERENCE = "reference", "Reference"
        CERTIFICATE = "certificate", "Certificate"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guard = models.ForeignKey(GuardProfile, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="guard_documents/%Y/%m/", blank=True)
    reference_number = models.CharField(max_length=120, blank=True)
    expires_on = models.DateField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_guard_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.guard} - {self.title}"


class GuardPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="guard_posts")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    geofence_radius_m = models.PositiveIntegerField(default=150)
    required_credentials = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_guard_posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["site__name", "name"]
        unique_together = ("site", "name")

    def __str__(self) -> str:
        return f"{self.name} @ {self.site.name}"


class PostOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GuardPost, on_delete=models.CASCADE, related_name="post_orders")
    title = models.CharField(max_length=160)
    body = models.TextField()
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_post_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["post", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} - {self.post}"


class Shift(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GuardPost, on_delete=models.CASCADE, related_name="shifts")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    required_guards = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_guard_shifts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["post", "starts_at"], name="guard_shift_post_start_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.post} - {self.starts_at:%Y-%m-%d %H:%M}"

    def clean(self):
        allowed = {
            self.Status.DRAFT: {self.Status.PUBLISHED, self.Status.CANCELLED},
            self.Status.PUBLISHED: {self.Status.IN_PROGRESS, self.Status.CANCELLED},
            self.Status.IN_PROGRESS: {self.Status.COMPLETED, self.Status.CANCELLED},
            self.Status.COMPLETED: set(),
            self.Status.CANCELLED: set(),
        }
        _validate_initial_status(self, {self.Status.DRAFT, self.Status.PUBLISHED}, label="Shift")
        _validate_status_transition(self, allowed, label="Shift")


class ShiftAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CLOCKED_IN = "clocked_in", "Clocked In"
        CLOCKED_OUT = "clocked_out", "Clocked Out"
        NO_SHOW = "no_show", "No Show"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="assignments")
    guard = models.ForeignKey(GuardProfile, on_delete=models.CASCADE, related_name="shift_assignments")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ASSIGNED, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_guard_shifts",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    clocked_in_at = models.DateTimeField(null=True, blank=True)
    clocked_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["shift__starts_at", "guard__last_name"]
        unique_together = ("shift", "guard")

    def __str__(self) -> str:
        return f"{self.guard} -> {self.shift}"

    def clean(self):
        allowed = {
            self.Status.ASSIGNED: {self.Status.ACCEPTED, self.Status.DECLINED, self.Status.NO_SHOW, self.Status.REMOVED},
            self.Status.ACCEPTED: {self.Status.CLOCKED_IN, self.Status.DECLINED, self.Status.NO_SHOW, self.Status.REMOVED},
            self.Status.DECLINED: {self.Status.ACCEPTED, self.Status.REMOVED},
            self.Status.CLOCKED_IN: {self.Status.CLOCKED_OUT},
            self.Status.CLOCKED_OUT: set(),
            self.Status.NO_SHOW: set(),
            self.Status.REMOVED: set(),
        }
        _validate_status_transition(self, allowed, label="Assignment")


class ClockEvent(models.Model):
    class EventType(models.TextChoices):
        CLOCK_IN = "clock_in", "Clock In"
        CLOCK_OUT = "clock_out", "Clock Out"
        BREAK_START = "break_start", "Break Start"
        BREAK_END = "break_end", "Break End"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(ShiftAssignment, on_delete=models.CASCADE, related_name="clock_events")
    event_type = models.CharField(max_length=24, choices=EventType.choices, db_index=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    within_geofence = models.BooleanField(default=False)
    device_timestamp = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} - {self.assignment}"


class Checkpoint(models.Model):
    class CheckpointType(models.TextChoices):
        QR = "qr", "QR"
        NFC = "nfc", "NFC"
        GPS = "gps", "GPS"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GuardPost, on_delete=models.CASCADE, related_name="checkpoints")
    name = models.CharField(max_length=160)
    checkpoint_type = models.CharField(max_length=16, choices=CheckpointType.choices, default=CheckpointType.QR)
    code = models.CharField(max_length=128, unique=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    geofence_radius_m = models.PositiveIntegerField(default=50)
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["post", "name"]

    def __str__(self) -> str:
        return f"{self.name} - {self.post}"


class PatrolRoute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GuardPost, on_delete=models.CASCADE, related_name="patrol_routes")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    expected_duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    checkpoints = models.ManyToManyField(Checkpoint, through="PatrolRouteCheckpoint", related_name="patrol_routes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["post", "name"]
        unique_together = ("post", "name")

    def __str__(self) -> str:
        return f"{self.name} - {self.post}"


class PatrolRouteCheckpoint(models.Model):
    route = models.ForeignKey(PatrolRoute, on_delete=models.CASCADE)
    checkpoint = models.ForeignKey(Checkpoint, on_delete=models.CASCADE)
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["sequence"]
        unique_together = (("route", "checkpoint"), ("route", "sequence"))

    def __str__(self) -> str:
        return f"{self.route} #{self.sequence}: {self.checkpoint}"


class PatrolRound(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(PatrolRoute, on_delete=models.CASCADE, related_name="rounds")
    assignment = models.ForeignKey(
        ShiftAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrol_rounds",
    )
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["status", "scheduled_start"], name="patrol_status_start_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.route} - {self.scheduled_start:%Y-%m-%d %H:%M}"

    def clean(self):
        allowed = {
            self.Status.SCHEDULED: {self.Status.IN_PROGRESS, self.Status.MISSED, self.Status.CANCELLED},
            self.Status.IN_PROGRESS: {self.Status.COMPLETED, self.Status.MISSED, self.Status.CANCELLED},
            self.Status.COMPLETED: set(),
            self.Status.MISSED: set(),
            self.Status.CANCELLED: set(),
        }
        _validate_initial_status(self, {self.Status.SCHEDULED}, label="Patrol round")
        _validate_status_transition(self, allowed, label="Patrol round")


class CheckpointScan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patrol_round = models.ForeignKey(PatrolRound, on_delete=models.CASCADE, related_name="scans")
    checkpoint = models.ForeignKey(Checkpoint, on_delete=models.CASCADE, related_name="scans")
    guard = models.ForeignKey(GuardProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkpoint_scans")
    scanned_at = models.DateTimeField(default=timezone.now, db_index=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    within_geofence = models.BooleanField(default=False)
    offline_created_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scanned_at"]
        indexes = [
            models.Index(fields=["checkpoint", "-scanned_at"], name="checkpoint_scan_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.checkpoint} scanned at {self.scanned_at:%Y-%m-%d %H:%M}"


class FieldReport(models.Model):
    class ReportType(models.TextChoices):
        DAILY_ACTIVITY = "daily_activity", "Daily Activity"
        INCIDENT = "incident", "Incident"
        MAINTENANCE = "maintenance", "Maintenance"
        VISITOR = "visitor", "Visitor"
        PARKING = "parking", "Parking"
        PASS_ON = "pass_on", "Pass-on"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="guard_reports")
    post = models.ForeignKey(GuardPost, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    assignment = models.ForeignKey(
        ShiftAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    guard = models.ForeignKey(GuardProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    report_type = models.CharField(max_length=32, choices=ReportType.choices, db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    report_data = models.JSONField(default=dict, blank=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    visible_to_client = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_guard_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["site", "-submitted_at"], name="guard_report_site_time_idx"),
            models.Index(fields=["report_type", "status"], name="guard_report_type_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} - {self.site} - {self.submitted_at:%Y-%m-%d}"

    def clean(self):
        allowed = {
            self.Status.DRAFT: {self.Status.SUBMITTED},
            self.Status.SUBMITTED: {self.Status.APPROVED, self.Status.REJECTED},
            self.Status.APPROVED: set(),
            self.Status.REJECTED: set(),
        }
        _validate_initial_status(self, {self.Status.DRAFT, self.Status.SUBMITTED}, label="Report")
        _validate_status_transition(self, allowed, label="Report")


class FieldReportAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(FieldReport, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="guard_reports/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Attachment for {self.report}"


class GuardLocationPing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guard = models.ForeignKey(GuardProfile, on_delete=models.CASCADE, related_name="location_pings")
    assignment = models.ForeignKey(
        ShiftAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_pings",
    )
    latitude = models.DecimalField(max_digits=12, decimal_places=9)
    longitude = models.DecimalField(max_digits=12, decimal_places=9)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed_mps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    heading_deg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    device_timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["guard", "-created_at"], name="guard_location_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.guard} @ {self.created_at:%Y-%m-%d %H:%M}"


class WelfareCheck(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        MISSED = "missed", "Missed"
        ESCALATED = "escalated", "Escalated"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(ShiftAssignment, on_delete=models.CASCADE, related_name="welfare_checks")
    due_at = models.DateTimeField(db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    response_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at"]

    def __str__(self) -> str:
        return f"Welfare check for {self.assignment} due {self.due_at:%Y-%m-%d %H:%M}"


class GuardPanicAlert(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guard = models.ForeignKey(GuardProfile, on_delete=models.CASCADE, related_name="panic_alerts")
    assignment = models.ForeignKey(
        ShiftAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panic_alerts",
    )
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="guard_panic_alerts")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN, db_index=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    note = models.TextField(blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_guard_panic_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_guard_panic_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Panic alert - {self.guard} - {self.status}"

    def clean(self):
        allowed = {
            self.Status.OPEN: {self.Status.ACKNOWLEDGED, self.Status.RESOLVED, self.Status.CANCELLED},
            self.Status.ACKNOWLEDGED: {self.Status.RESOLVED, self.Status.CANCELLED},
            self.Status.RESOLVED: set(),
            self.Status.CANCELLED: set(),
        }
        _validate_initial_status(self, {self.Status.OPEN}, label="Panic alert")
        _validate_status_transition(self, allowed, label="Panic alert")


class DispatchTask(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted"
        EN_ROUTE = "en_route", "En Route"
        ARRIVED = "arrived", "Arrived"
        RESOLVED = "resolved", "Resolved"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="guard_dispatch_tasks")
    assigned_guard = models.ForeignKey(
        GuardProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_tasks",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN, db_index=True)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    target_latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    target_longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    alarm_event = models.ForeignKey(
        "alarms.AlarmEvent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_dispatch_tasks",
    )
    emergency_request = models.ForeignKey(
        "emergency.EmergencyRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_dispatch_tasks",
    )
    panic_alert = models.ForeignKey(
        GuardPanicAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_guard_dispatch_tasks",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    en_route_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority", "-created_at"], name="dispatch_status_prio_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.status}"

    def clean(self):
        allowed = {
            self.Status.OPEN: {self.Status.ASSIGNED, self.Status.CANCELLED},
            self.Status.ASSIGNED: {self.Status.ACCEPTED, self.Status.CANCELLED},
            self.Status.ACCEPTED: {self.Status.EN_ROUTE, self.Status.CANCELLED},
            self.Status.EN_ROUTE: {self.Status.ARRIVED, self.Status.CANCELLED},
            self.Status.ARRIVED: {self.Status.RESOLVED, self.Status.CANCELLED},
            self.Status.RESOLVED: set(),
            self.Status.CANCELLED: set(),
        }
        _validate_initial_status(self, {self.Status.OPEN, self.Status.ASSIGNED}, label="Dispatch task")
        if self.status == self.Status.ASSIGNED and self.assigned_guard_id is None:
            raise ValidationError({"assigned_guard": "A guard is required for assigned dispatch tasks."})
        _validate_status_transition(self, allowed, label="Dispatch task")
