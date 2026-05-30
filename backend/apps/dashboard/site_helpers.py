"""Site console helpers: zones, faults, and alarm inventory."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from django.utils.timesince import timesince

from apps.alarms.models import AlarmEvent as Event
from apps.dashboard.event_presenters import should_hide_console_event
from apps.sites.models import (
    AlarmOutput,
    AlarmPanelDevice,
    AlarmPeripheral,
    OperationsZone,
    Site,
    Subsystem,
    Zone,
)

def _normalize_zone_color(color: str, default: str = "#6366f1") -> str:
    value = (color or "").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.lower()
        except ValueError:
            pass
    return default


def _operations_zone_name_taken(name: str, *, exclude_pk=None) -> bool:
    qs = OperationsZone.objects.filter(name__iexact=name.strip())
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _operations_zones_for_site(site=None):
    qs = OperationsZone.objects.all()
    if site is not None:
        qs = qs.filter(Q(is_active=True) | Q(pk=site.operations_zone_id))
    else:
        qs = qs.filter(is_active=True)
    return qs.order_by("sort_order", "name")


def _assign_site_operations_zone(site, zone_id: str) -> None:
    zone_id = (zone_id or "").strip()
    if not zone_id:
        site.operations_zone = None
        return
    site.operations_zone = OperationsZone.objects.filter(pk=zone_id).first()

def _visible_console_events(site: Site, *, limit: int = 15) -> list[Event]:
    # Pull a slightly wider slice so we can suppress duplicate snapshot rows
    # without starving the compact feed.
    candidates = list(
        Event.objects.filter(site=site)
        .select_related("site", "subsystem", "zone")
        .order_by("-occurred_at")[: limit * 3]
    )
    visible = [event for event in candidates if not should_hide_console_event(event)]
    return visible[:limit]


def _fault_age_label(timestamp):
    if not timestamp:
        return "current"
    return f"{timesince(timestamp, timezone.now())} ago"


def _is_problem_status(value) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return normalized not in {"ok", "normal", "online", "available", "good", "none", "unknown"}


def _build_active_faults(site: Site, *, limit: int | None = None) -> list[dict]:
    """
    Build current active faults from the latest device/zone health state.

    Historical alarm events remain in the event feed. The active-fault banner
    should only show things that are still true in the local status snapshot.
    """
    faults = []

    def add_fault(*, item_id, label, source, detail="", severity="critical", timestamp=None):
        faults.append(
            {
                "id": item_id,
                "label": label,
                "source": source,
                "detail": detail,
                "severity": severity,
                "age": _fault_age_label(timestamp),
                "_sort_at": timestamp or timezone.now(),
            }
        )

    devices = site.devices.prefetch_related("subsystems__zones", "peripherals", "outputs")
    for device in devices:
        device_seen_at = device.last_seen_at or device.last_health_check or device.updated_at
        if not device.is_online:
            add_fault(
                item_id=f"panel:{device.id}:offline",
                label="Panel Offline",
                source=device.name,
                detail=device.serial_number,
                timestamp=device_seen_at,
            )
        if device.normalized_battery_status == AlarmPanelDevice.BATTERY_LOW:
            add_fault(
                item_id=f"panel:{device.id}:battery",
                label="Panel Battery Low",
                source=device.name,
                detail=device.power_status_label,
                severity="high",
                timestamp=device.updated_at,
            )
        if str(device.work_status or "").strip().lower() == AlarmPanelDevice.WORK_ALARM:
            add_fault(
                item_id=f"panel:{device.id}:alarm",
                label="Panel In Alarm",
                source=device.name,
                detail=device.work_status,
                timestamp=device.updated_at,
            )

        for subsystem in device.subsystems.all():
            for zone in subsystem.zones.all():
                zone_seen_at = zone.last_seen_at or zone.updated_at
                if zone.state == Zone.STATE_ALARM:
                    add_fault(
                        item_id=f"zone:{zone.id}:alarm",
                        label="Zone Alarm",
                        source=zone.name,
                        detail=subsystem.name,
                        timestamp=zone_seen_at,
                    )
                elif zone.state == Zone.STATE_OPEN and subsystem.status != Subsystem.STATUS_DISARMED:
                    add_fault(
                        item_id=f"zone:{zone.id}:open",
                        label="Zone Open",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone_seen_at,
                    )
                if not zone.is_online:
                    add_fault(
                        item_id=f"zone:{zone.id}:offline",
                        label="Sensor Offline",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone_seen_at,
                    )
                if zone.low_battery:
                    add_fault(
                        item_id=f"zone:{zone.id}:battery",
                        label="Sensor Battery Low",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone.updated_at,
                    )
                if zone.tamper:
                    add_fault(
                        item_id=f"zone:{zone.id}:tamper",
                        label="Sensor Tamper",
                        source=zone.name,
                        detail=subsystem.name,
                        timestamp=zone.updated_at,
                    )
                if zone.shielded:
                    add_fault(
                        item_id=f"zone:{zone.id}:shielded",
                        label="Sensor Shielded",
                        source=zone.name,
                        detail=subsystem.name,
                        severity="high",
                        timestamp=zone.updated_at,
                    )

        for peripheral in device.peripherals.all():
            source = peripheral.name
            timestamp = peripheral.updated_at
            if not peripheral.is_online:
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:offline",
                    label="Peripheral Offline",
                    source=source,
                    detail=peripheral.peripheral_type_label or peripheral.peripheral_type,
                    severity="high",
                    timestamp=timestamp,
                )
            if _is_problem_status(peripheral.battery_status):
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:battery",
                    label="Peripheral Battery Issue",
                    source=source,
                    detail=peripheral.battery_status,
                    severity="high",
                    timestamp=timestamp,
                )
            if peripheral.tamper:
                add_fault(
                    item_id=f"peripheral:{peripheral.id}:tamper",
                    label="Peripheral Tamper",
                    source=source,
                    detail=peripheral.peripheral_type_label or peripheral.peripheral_type,
                    timestamp=timestamp,
                )

        for output in device.outputs.all():
            if output.status == AlarmOutput.STATUS_NOT_RELATED or not output.is_available:
                continue
            source = output.name
            timestamp = output.updated_at
            if not output.is_online:
                add_fault(
                    item_id=f"output:{output.id}:offline",
                    label="Output Offline",
                    source=source,
                    detail=output.serial_number,
                    severity="high",
                    timestamp=timestamp,
                )
            if output.tamper:
                add_fault(
                    item_id=f"output:{output.id}:tamper",
                    label="Output Tamper",
                    source=source,
                    detail=output.access_module_type or "output module",
                    timestamp=timestamp,
                )
            if _is_problem_status(output.battery_status):
                add_fault(
                    item_id=f"output:{output.id}:battery",
                    label="Output Battery Issue",
                    source=source,
                    detail=output.battery_status,
                    severity="high",
                    timestamp=timestamp,
                )

    faults.sort(key=lambda item: item["_sort_at"], reverse=True)
    for fault in faults:
        fault.pop("_sort_at", None)
    if limit is not None:
        return faults[:limit]
    return faults

def _build_display_alarm_peripherals(site: Site):
    actual_peripherals = list(
        AlarmPeripheral.objects.filter(site=site)
        .select_related("device")
        .order_by("peripheral_type", "peripheral_number")
    )
    display_peripherals = []

    for peripheral in actual_peripherals:
        display_peripherals.append(
            {
                "id": str(peripheral.id),
                "name": peripheral.name,
                "display_type": peripheral.get_peripheral_type_display(),
                "serial_number": peripheral.serial_number,
                "is_online": peripheral.is_online,
                "battery_status": peripheral.battery_status,
                "signal_strength": peripheral.signal_strength,
                "network_status": peripheral.network_status,
                "tamper": peripheral.tamper,
                "peripheral_type": peripheral.peripheral_type,
                "peripheral_number": peripheral.peripheral_number,
                "source": "hik",
            }
        )

    display_peripherals.sort(key=lambda item: (item["peripheral_type"], item["peripheral_number"], item["name"]))
    return display_peripherals


def _filter_installed_module_peripherals(display_peripherals: list[dict]) -> list[dict]:
    module_types = {
        AlarmPeripheral.TYPE_OUTPUT_MODULE,
        AlarmPeripheral.TYPE_REPEATER,
        AlarmPeripheral.TYPE_SIREN,
        AlarmPeripheral.TYPE_TRANSMITTER,
    }
    return [
        item
        for item in display_peripherals
        if item["peripheral_type"] in module_types
    ]


def _filter_installed_alarm_outputs(site: Site):
    return (
        AlarmOutput.objects.filter(site=site)
        .exclude(status=AlarmOutput.STATUS_NOT_RELATED)
        .select_related("device")
        .order_by("output_number")
    )


def _compute_alarm_inventory_counts(site: Site, display_peripherals: list[dict]) -> dict:
    peripheral_counts = {}
    for item in display_peripherals:
        peripheral_counts[item["peripheral_type"]] = peripheral_counts.get(item["peripheral_type"], 0) + 1
    installed_outputs_count = _filter_installed_alarm_outputs(site).count()

    return {
        "zones": Zone.objects.filter(subsystem__site=site, device_type=Zone.DEVICE_TYPE_ZONE).count(),
        "keypads": peripheral_counts.get(AlarmPeripheral.TYPE_KEYPAD, 0),
        "keyfobs": peripheral_counts.get(AlarmPeripheral.TYPE_KEYFOB, 0),
        "card_readers": peripheral_counts.get(AlarmPeripheral.TYPE_CARD_READER, 0),
        "sirens": peripheral_counts.get(AlarmPeripheral.TYPE_SIREN, 0),
        "repeaters": peripheral_counts.get(AlarmPeripheral.TYPE_REPEATER, 0),
        "transmitters": peripheral_counts.get(AlarmPeripheral.TYPE_TRANSMITTER, 0),
        "output_modules": peripheral_counts.get(AlarmPeripheral.TYPE_OUTPUT_MODULE, 0),
        "outputs": installed_outputs_count,
    }


# Public names used by views_ops / views_sites
normalize_zone_color = _normalize_zone_color
operations_zone_name_taken = _operations_zone_name_taken
operations_zones_for_site = _operations_zones_for_site
assign_site_operations_zone = _assign_site_operations_zone
visible_console_events = _visible_console_events
build_active_faults = _build_active_faults
build_display_alarm_peripherals = _build_display_alarm_peripherals
filter_installed_module_peripherals = _filter_installed_module_peripherals
filter_installed_alarm_outputs = _filter_installed_alarm_outputs
compute_alarm_inventory_counts = _compute_alarm_inventory_counts
