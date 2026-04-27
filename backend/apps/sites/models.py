import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Site(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True, help_text="State/Province/Region")
    country = models.CharField(max_length=120, blank=True)
    hik_site_id = models.CharField(max_length=128, unique=True)
    timezone = models.CharField(max_length=64, default="UTC")
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Industry / Scenario categorization ("Scenes")
    primary_industry = models.CharField(max_length=128, blank=True)
    secondary_industry = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class HikSiteDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="hik_devices")
    hik_device_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=128, unique=True)
    device_category = models.IntegerField(null=True, blank=True)
    device_sub_category = models.IntegerField(null=True, blank=True)
    device_type = models.CharField(max_length=128, blank=True, default="")
    device_version = models.CharField(max_length=128, blank=True, default="")
    is_online = models.BooleanField(default=False)
    is_subscribed = models.BooleanField(default=False)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["device_category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"


class SubscriptionPackage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    grace_period_days = models.PositiveSmallIntegerField(default=7)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monthly_rate"]

    def __str__(self) -> str:
        return f"{self.name} — GH₵{self.monthly_rate}/mo"


class Subscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_OVERDUE = "overdue"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.OneToOneField(
        Site, on_delete=models.CASCADE, related_name="subscription"
    )
    package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="subscriptions",
    )
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    billing_day = models.PositiveSmallIntegerField(
        default=1,
        help_text="Day of the month the subscription is due (1–28).",
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    next_due_date = models.DateField()
    grace_period_days = models.PositiveSmallIntegerField(
        default=7,
        help_text="Days after due date before the subscription is automatically suspended.",
    )
    suspended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_access_blocked(self) -> bool:
        return self.status in (self.STATUS_SUSPENDED, self.STATUS_CANCELLED)

    @classmethod
    def classify_status(cls, *, next_due_date, grace_period_days, today=None) -> str:
        today = today or timezone.localdate()
        if next_due_date >= today:
            return cls.STATUS_ACTIVE
        if today <= next_due_date + timedelta(days=grace_period_days):
            return cls.STATUS_OVERDUE
        return cls.STATUS_SUSPENDED

    def apply_due_date_status(self, *, today=None) -> str:
        if self.status == self.STATUS_CANCELLED:
            return self.status

        next_status = self.classify_status(
            next_due_date=self.next_due_date,
            grace_period_days=self.grace_period_days,
            today=today,
        )
        self.status = next_status
        if next_status == self.STATUS_SUSPENDED:
            self.suspended_at = self.suspended_at or timezone.now()
        else:
            self.suspended_at = None
        return next_status

    def sync_next_due_date_from_latest_payment(self) -> bool:
        latest_payment = self.payments.order_by("-period_end", "-paid_at").first()
        if latest_payment is None:
            return False

        self.next_due_date = latest_payment.period_end + timedelta(days=1)
        self.apply_due_date_status()
        return True

    def suspend(self) -> None:
        self.status = self.STATUS_SUSPENDED
        self.suspended_at = timezone.now()
        self.save(update_fields=["status", "suspended_at", "updated_at"])

    def reactivate(self, new_due_date=None) -> None:
        import calendar

        if new_due_date is None:
            today = timezone.localdate()
            # Next occurrence of billing_day
            day = min(self.billing_day, calendar.monthrange(today.year, today.month)[1])
            candidate = today.replace(day=day)
            if candidate <= today:
                # Move to next month
                if today.month == 12:
                    candidate = candidate.replace(year=today.year + 1, month=1)
                else:
                    candidate = candidate.replace(month=today.month + 1)
            new_due_date = candidate
        self.next_due_date = new_due_date
        if self.status == self.STATUS_CANCELLED:
            self.status = self.STATUS_ACTIVE
        self.apply_due_date_status()
        self.save(update_fields=["status", "suspended_at", "next_due_date", "updated_at"])

    def __str__(self) -> str:
        return f"{self.site.name} — {self.get_status_display()}"


class SubscriptionPayment(models.Model):
    METHOD_CASH = "cash"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_BANK_TRANSFER = "bank_transfer"
    METHOD_CARD = "card"
    METHOD_OTHER = "other"
    METHOD_CHOICES = (
        (METHOD_CASH, "Cash"),
        (METHOD_MOBILE_MONEY, "Mobile Money"),
        (METHOD_BANK_TRANSFER, "Bank Transfer"),
        (METHOD_CARD, "Card"),
        (METHOD_OTHER, "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    period_start = models.DateField()
    period_end = models.DateField()
    method = models.CharField(max_length=32, choices=METHOD_CHOICES, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.subscription.site.name} — {self.paid_at.date()} — {self.amount}"


class CustomerSiteAccess(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_VIEWER, "Viewer"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="access_list")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_OWNER)
    can_control_alarm = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "site")

    def __str__(self) -> str:
        return f"{self.user} -> {self.site}"


class AlarmPanelDevice(models.Model):
    DEVICE_TYPE_PANEL = "panel"
    DEVICE_TYPE_CHOICES = ((DEVICE_TYPE_PANEL, "Panel"),)

    BATTERY_OK = "ok"
    BATTERY_LOW = "low"
    BATTERY_UNKNOWN = "unknown"

    WORK_ALARM = "alarm"
    WORK_PART_ARM = "partArm"
    WORK_ARMED = "armed"
    WORK_DISARMED = "allDisArm"
    WORK_UNKNOWN = "unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=128, unique=True)
    hik_device_id = models.CharField(max_length=128, unique=True)
    device_type = models.CharField(
        max_length=32, choices=DEVICE_TYPE_CHOICES, default=DEVICE_TYPE_PANEL
    )
    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    # E1: deviceSubCategory from §3.21 — identifies AX Pro variant:
    # 3=AX2, 4=AX Hub, 5=AX Hybrid, 10=AX Hybrid Pro (None = unknown / not returned by API)
    hik_device_sub_category = models.IntegerField(null=True, blank=True)
    # Health report fields (updated by poll_device_health Celery task)
    battery_status = models.CharField(max_length=16, default=BATTERY_UNKNOWN)
    work_status = models.CharField(max_length=16, default=WORK_UNKNOWN)
    cloud_status = models.CharField(max_length=16, default="unknown")
    last_health_check = models.DateTimeField(null=True, blank=True)
    model_number = models.CharField(max_length=128, blank=True, default="")
    firmware_version = models.CharField(max_length=128, blank=True, default="")
    hardware_version = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def normalize_battery_status_value(cls, raw_value: str | None) -> str:
        value = str(raw_value or "").strip().lower()
        compact = value.replace(" ", "").replace("_", "").replace("-", "")
        if compact in {"ok", "normal", "ac", "mains", "onac", "mainspower", "externalpower", "good"}:
            return cls.BATTERY_OK
        if compact in {"low", "lowpower", "dc", "battery", "backupbattery", "onbattery"}:
            return cls.BATTERY_LOW
        return cls.BATTERY_UNKNOWN

    @property
    def normalized_battery_status(self) -> str:
        return self.normalize_battery_status_value(self.battery_status)

    @property
    def power_status_label(self) -> str:
        if not self.is_online:
            return "Offline"
        if self.normalized_battery_status == self.BATTERY_OK:
            return "Mains OK"
        if self.normalized_battery_status == self.BATTERY_LOW:
            return "Battery Low"
        if self.last_health_check:
            return "Power Unverified"
        return "Awaiting Sync"

    @property
    def power_status_tone(self) -> str:
        if not self.is_online:
            return "muted"
        if self.normalized_battery_status == self.BATTERY_OK:
            return "ok"
        if self.normalized_battery_status == self.BATTERY_LOW:
            return "alert"
        return "muted"

    def __str__(self) -> str:
        return self.name


class Subsystem(models.Model):
    STATUS_DISARMED = "disarmed"
    STATUS_ARMED = "armed"
    STATUS_STAY = "stay"
    STATUS_ALARM = "alarm"
    STATUS_CHOICES = (
        (STATUS_DISARMED, "Disarmed"),
        (STATUS_ARMED, "Armed"),
        (STATUS_STAY, "Stay Armed"),
        (STATUS_ALARM, "Alarm"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="subsystems")
    device = models.ForeignKey(
        AlarmPanelDevice,
        on_delete=models.CASCADE,
        related_name="subsystems",
    )
    name = models.CharField(max_length=255)
    hik_subsystem_id = models.CharField(max_length=128, unique=True)
    subsystem_number = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_DISARMED,
    )
    # E2: Remaining exit/entry delay in seconds from §A.5.9 SubSys.delayTime
    # Valid when arming status is 'stay' or 'away'. None = not in delay or not supported.
    delay_time_remaining = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Zone(models.Model):
    STATE_NORMAL = "normal"
    STATE_OPEN = "open"
    STATE_ALARM = "alarm"
    STATE_BYPASSED = "bypassed"
    STATE_CHOICES = (
        (STATE_NORMAL, "Normal"),
        (STATE_OPEN, "Open"),
        (STATE_ALARM, "Alarm"),
        (STATE_BYPASSED, "Bypassed"),
    )

    DEVICE_TYPE_ZONE = "zone"
    DEVICE_TYPE_KEYPAD = "keypad"
    DEVICE_TYPE_KEYFOB = "keyfob"
    DEVICE_TYPE_CARD_READER = "card_reader"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.CASCADE,
        related_name="zones",
    )
    name = models.CharField(max_length=255)
    zone_number = models.PositiveIntegerField()
    device_type = models.CharField(max_length=16, default=DEVICE_TYPE_ZONE)
    # device_number: actual panel enrollment slot (deviceNo from ISAPI ZoneList, e.g. 2,3,4,5)
    device_number = models.PositiveIntegerField(null=True, blank=True)
    # detector_type: sensor type string from ISAPI (e.g. 'slimMagneticContact', 'passiveInfraredDetector', 'pircam')
    detector_type = models.CharField(max_length=64, blank=True, default="")
    zone_type = models.CharField(max_length=32, blank=True, default="")
    reason = models.CharField(max_length=32, blank=True, default="")
    health_status = models.CharField(max_length=32, blank=True, default="")
    model_number = models.CharField(max_length=128, blank=True, default="")
    access_module_type = models.CharField(max_length=32, blank=True, default="")
    related_access_module_id = models.PositiveIntegerField(null=True, blank=True)
    module_address = models.PositiveIntegerField(null=True, blank=True)
    zone_attribute = models.CharField(max_length=16, blank=True, default="")
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default=STATE_NORMAL)
    # Health fields (updated by poll_device_health Celery task via site/health/report API)
    low_battery = models.BooleanField(default=False)
    tamper = models.BooleanField(default=False)
    shielded = models.BooleanField(default=False)
    magnet_open = models.BooleanField(null=True, blank=True)
    signal_strength = models.CharField(max_length=16, blank=True, default="")
    diagnostics_result = models.CharField(max_length=32, blank=True, default="")
    network_status = models.CharField(max_length=16, blank=True, default="")
    external_power = models.CharField(max_length=32, blank=True, default="")
    main_charge = models.CharField(max_length=16, blank=True, default="")
    preheat_status = models.CharField(max_length=16, blank=True, default="")
    useful_life_status = models.CharField(max_length=16, blank=True, default="")
    maze_status = models.CharField(max_length=16, blank=True, default="")
    sensor_status = models.CharField(max_length=16, blank=True, default="")
    temperature = models.IntegerField(null=True, blank=True)
    humidity = models.IntegerField(null=True, blank=True)
    # E3: Battery charge level (0-100) from §A.5.13 Zone.chargeValue; None = not reported
    charge_value = models.PositiveSmallIntegerField(null=True, blank=True)
    is_online = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("subsystem", "zone_number", "device_type")

    def __str__(self) -> str:
        return self.name

    @property
    def display_type(self) -> str:
        from apps.hik_adapter.services import HikPartnerService
        if self.device_type == self.DEVICE_TYPE_KEYFOB:
            return "Keyfob"
        if self.device_type == self.DEVICE_TYPE_KEYPAD:
            return "Keypad"
        return HikPartnerService.get_detector_label(self.detector_type)

    @property
    def icon_type(self) -> str:
        from apps.hik_adapter.services import HikPartnerService
        if self.device_type == self.DEVICE_TYPE_KEYFOB:
            return "key"
        if self.device_type == self.DEVICE_TYPE_KEYPAD:
            return "keyboard"
        return HikPartnerService.get_detector_icon(self.detector_type)


class AlarmPeripheral(models.Model):
    TYPE_KEYPAD = "keypad"
    TYPE_KEYFOB = "keyfob"
    TYPE_CARD_READER = "card_reader"
    TYPE_OUTPUT_MODULE = "output_module"
    TYPE_REPEATER = "repeater"
    TYPE_SIREN = "siren"
    TYPE_TRANSMITTER = "transmitter"

    TYPE_CHOICES = (
        (TYPE_KEYPAD, "Keypad"),
        (TYPE_KEYFOB, "Keyfob"),
        (TYPE_CARD_READER, "Card Reader"),
        (TYPE_OUTPUT_MODULE, "Output Module"),
        (TYPE_REPEATER, "Repeater"),
        (TYPE_SIREN, "Siren"),
        (TYPE_TRANSMITTER, "Transmitter"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="alarm_peripherals")
    device = models.ForeignKey(
        AlarmPanelDevice,
        on_delete=models.CASCADE,
        related_name="peripherals",
    )
    peripheral_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    peripheral_number = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=128, blank=True, default="")
    peripheral_type_label = models.CharField(max_length=64, blank=True, default="")
    diagnostics_result = models.CharField(max_length=32, blank=True, default="")
    network_status = models.CharField(max_length=16, blank=True, default="")
    battery_status = models.CharField(max_length=16, blank=True, default="")
    signal_strength = models.CharField(max_length=16, blank=True, default="")
    tamper = models.BooleanField(default=False)
    bypassed = models.BooleanField(default=False)
    external_power = models.CharField(max_length=32, blank=True, default="")
    is_online = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_operation_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("device", "peripheral_type", "peripheral_number")

    def __str__(self) -> str:
        return f"{self.get_peripheral_type_display()} {self.peripheral_number} @ {self.device.name}"


class AlarmOutput(models.Model):
    STATUS_ON = "on"
    STATUS_OFF = "off"
    STATUS_OFFLINE = "offline"
    STATUS_NOT_RELATED = "notRelated"
    STATUS_HEARTBEAT_ABNORMAL = "heartbeatAbnormal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="alarm_outputs")
    device = models.ForeignKey(
        AlarmPanelDevice,
        on_delete=models.CASCADE,
        related_name="outputs",
    )
    output_number = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, blank=True, default="")
    tamper = models.BooleanField(default=False)
    battery_status = models.CharField(max_length=16, blank=True, default="")
    signal_strength = models.CharField(max_length=16, blank=True, default="")
    linkage = models.CharField(max_length=32, blank=True, default="")
    duration_const_output_enable = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    access_module_type = models.CharField(max_length=32, blank=True, default="")
    related_access_module_id = models.PositiveIntegerField(null=True, blank=True)
    module_address = models.PositiveIntegerField(null=True, blank=True)
    subsystem_numbers = models.JSONField(default=list, blank=True)
    scenario_types = models.JSONField(default=list, blank=True)
    relay_attribute = models.CharField(max_length=16, blank=True, default="")
    device_number = models.PositiveIntegerField(null=True, blank=True)
    model_number = models.CharField(max_length=128, blank=True, default="")
    diagnostics_result = models.CharField(max_length=32, blank=True, default="")
    network_status = models.CharField(max_length=16, blank=True, default="")
    is_online = models.BooleanField(default=True)
    serial_number = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("device", "output_number")

    def __str__(self) -> str:
        return f"Output {self.output_number} @ {self.device.name}"
