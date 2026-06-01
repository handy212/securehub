import json
import xml.etree.ElementTree as ET
import logging
import re
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone as dt_timezone

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.alarms.event_labels import humanize_event_label, normalize_event_label_lookup
from apps.alarms.media import resolve_picture_media_type
from apps.alarms.models import AlarmEvent

logger = logging.getLogger(__name__)
from apps.sites.models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, HikSiteDevice, Site, Subsystem, Zone
from apps.sites.scenes import normalize_scene_label

from .client import HikPartnerClient
from .exceptions import HikPartnerError


class HikPartnerService:
    DETECTOR_TYPE_META = {
        "magneticContact": {"label": "Contact Sensor", "icon": "door"},
        "slimMagneticContact": {"label": "Contact Sensor", "icon": "door"},
        "rollerShutterContact": {"label": "Shutter Contact", "icon": "door"},
        "passiveInfraredDetector": {"label": "Motion Sensor", "icon": "motion"},
        "curtainDetector": {"label": "Curtain Motion", "icon": "motion"},
        "curtainPIRDetector": {"label": "Curtain Motion", "icon": "motion"},
        "triTechDetector": {"label": "Tri-Tech Motion", "icon": "motion"},
        "dualTechDetector": {"label": "Dual-Tech Motion", "icon": "motion"},
        "pircam": {"label": "Motion Cam", "icon": "camera"},
        "glassBreakDetector": {"label": "Glass Break", "icon": "window"},
        "shockDetector": {"label": "Shock Sensor", "icon": "sensor"},
        "vibrationDetector": {"label": "Vibration Sensor", "icon": "sensor"},
        "smokeDetector": {"label": "Smoke Detector", "icon": "fire"},
        "wirelessSmokeDetector": {"label": "Smoke Detector", "icon": "fire"},
        "heatDetector": {"label": "Heat Detector", "icon": "fire"},
        "temperatureDetector": {"label": "Temperature Sensor", "icon": "sensor"},
        "waterDetector": {"label": "Water Leak", "icon": "water"},
        "leakDetector": {"label": "Water Leak", "icon": "water"},
        "gasDetector": {"label": "Gas Leak", "icon": "gas"},
        "coDetector": {"label": "CO Detector", "icon": "gas"},
        "panicButton": {"label": "Panic Button", "icon": "emergency"},
        "emergencyButton": {"label": "Emergency Button", "icon": "emergency"},
        "medicalButton": {"label": "Medical Button", "icon": "emergency"},
        "sosButton": {"label": "SOS Button", "icon": "emergency"},
        "keyfob": {"label": "Keyfob", "icon": "key"},
        "keypad": {"label": "Keypad", "icon": "keyboard"},
        "cardReader": {"label": "Card Reader", "icon": "sensor"},
        "wirelessDetector": {"label": "Wireless Detector", "icon": "sensor"},
        "wireDetector": {"label": "Wired Detector", "icon": "sensor"},
        "detector": {"label": "Zone Sensor", "icon": "sensor"},
    }

    EVENT_META_BY_RAW_TYPE = {
        "linkage": {
            "normalized": "linkage_media",
            "display_name": "Linkage Media",
            "category": AlarmEvent.CATEGORY_INFO,
            "severity": AlarmEvent.SEVERITY_LOW,
        },
        "manualrep": {
            "normalized": "manual_capture",
            "display_name": "Manual Capture",
            "category": AlarmEvent.CATEGORY_INFO,
            "severity": AlarmEvent.SEVERITY_LOW,
        },
        "diskerror": {
            "normalized": "disk_error",
            "display_name": "Disk Error",
            "category": AlarmEvent.CATEGORY_HEALTH,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "diskfull": {
            "normalized": "disk_full",
            "display_name": "Disk Full",
            "category": AlarmEvent.CATEGORY_HEALTH,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "diskrecover": {
            "normalized": "disk_recovered",
            "display_name": "Disk Recovered",
            "category": AlarmEvent.CATEGORY_HEALTH,
            "severity": AlarmEvent.SEVERITY_LOW,
        },
        "fielddetection": {
            "normalized": "intrusion_detection",
            "display_name": "Intrusion Detection",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_CRITICAL,
        },
        "io": {
            "normalized": "io_alarm",
            "display_name": "I/O Alarm",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "linedetection": {
            "normalized": "line_crossing",
            "display_name": "Line Crossing",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "recordexception": {
            "normalized": "record_exception",
            "display_name": "Record Exception",
            "category": AlarmEvent.CATEGORY_HEALTH,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "regionentrance": {
            "normalized": "region_entrance",
            "display_name": "Region Entrance",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "regionexiting": {
            "normalized": "region_exit",
            "display_name": "Region Exit",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "shelteralarm": {
            "normalized": "video_tamper",
            "display_name": "Video Tamper",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "videoloss": {
            "normalized": "video_loss",
            "display_name": "Video Loss",
            "category": AlarmEvent.CATEGORY_HEALTH,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "vmd": {
            "normalized": "motion_detection",
            "display_name": "Motion Detection",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "alarmtrig": {
            "normalized": "alarm_triggered",
            "display_name": "Alarm Triggered",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_CRITICAL,
        },
        "firedetection": {
            "normalized": "fire_detection",
            "display_name": "Fire Detection",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_CRITICAL,
        },
        "yscallingevent": {
            "normalized": "intercom_call",
            "display_name": "Intercom Call",
            "category": AlarmEvent.CATEGORY_INFO,
            "severity": AlarmEvent.SEVERITY_LOW,
        },
        "tmpa": {
            "normalized": "thermal_alarm",
            "display_name": "Thermal Alarm",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "tma": {
            "normalized": "temperature_alarm",
            "display_name": "Temperature Alarm",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
        "tda": {
            "normalized": "temperature_difference_alarm",
            "display_name": "Temperature Difference Alarm",
            "category": AlarmEvent.CATEGORY_ALARM,
            "severity": AlarmEvent.SEVERITY_HIGH,
        },
    }

    EVENT_META_BY_DESC = {
        "arm": ("arm", "Arm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "awayarm": ("arm_away", "Arm Away", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "armaway": ("arm_away", "Arm Away", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "armed away": ("arm_away", "Arm Away", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "stay": ("stay_arm", "Stay Arm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "stayarm": ("stay_arm", "Stay Arm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "stayarmoperation": ("stay_arm", "Stay Arm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "disarm": ("disarm", "Disarm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "disarmoperation": ("disarm", "Disarm", AlarmEvent.CATEGORY_ARM, AlarmEvent.SEVERITY_LOW),
        "bypasszone": ("bypass_zone", "Zone Bypassed", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_MEDIUM),
        "bypassrecover": ("unbypass_zone", "Bypass Recovered", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "zonerestore": ("zone_restore", "Zone Restored", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "lowbattery": ("battery_low", "Low Battery", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "batterylow": ("battery_low", "Low Battery", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "acdown": ("ac_power_lost", "AC Power Lost", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "acrecov": ("ac_power_restored", "AC Power Restored", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
        "acrecover": ("ac_power_restored", "AC Power Restored", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
        "tamperalarm": ("tamper_alarm", "Tamper Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_HIGH),
        "deviceoffline": ("device_offline", "Device Offline", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "deviceonline": ("device_online", "Device Online", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
        "panicalarm": ("panic_alarm", "Panic Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "medicalalarm": ("medical_alarm", "Medical Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "firealarm": ("fire_alarm", "Fire Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "gasalarm": ("gas_alarm", "Gas Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "smartalarm": ("smart_alarm", "Smart Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_HIGH),
        "panellidopened": ("panel_lid_opened", "Panel Lid Opened", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_HIGH),
        "peripheraltamper": ("peripheral_tamper", "Peripheral Tamper", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_HIGH),
        "zonealarm": ("zone_alarm", "Zone Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "systemoperation": ("system_operation", "System Operation", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "mobilezoneinstantalarm": ("instant_zone_alarm", "Instant Zone Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "softzonepanicalarm": ("panic_alarm", "Panic Alarm", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
        "clearalarm": ("alarm_cleared", "Alarm Cleared", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "wirednetworkfault": ("wired_network_fault", "Wired Network Fault", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "wirednetworkfaultrecover": ("wired_network_fault_restored", "Wired Network Fault Restored", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
        "snapshot": ("snapshot_captured", "Snapshot Captured", AlarmEvent.CATEGORY_INFO, AlarmEvent.SEVERITY_LOW),
        "online": ("device_online", "Online", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_LOW),
        "offline": ("device_offline", "Offline", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "panelstatus(power&battery)": ("panel_power_status", "Panel Power Status", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_MEDIUM),
        "panelstatus(communications)": ("panel_communication_status", "Panel Communication Status", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_HIGH),
        "zonestatus": ("zone_status", "Zone Status", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_MEDIUM),
        "peripheralsstatus": ("peripheral_status", "Peripherals Status", AlarmEvent.CATEGORY_HEALTH, AlarmEvent.SEVERITY_MEDIUM),
        "panelupgrade": ("panel_upgrade", "Panel Upgrade", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "manualrep": ("manual_capture", "Manual Capture", AlarmEvent.CATEGORY_INFO, AlarmEvent.SEVERITY_LOW),
        "linkage": ("linkage_media", "Linkage Media", AlarmEvent.CATEGORY_INFO, AlarmEvent.SEVERITY_LOW),
        "addexmodule": ("module_added", "Module Added", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "delexmodule": ("module_removed", "Module Removed", AlarmEvent.CATEGORY_SYSTEM, AlarmEvent.SEVERITY_LOW),
        "alarmtrig": ("alarm_triggered", "Alarm Triggered", AlarmEvent.CATEGORY_ALARM, AlarmEvent.SEVERITY_CRITICAL),
    }

    NORMALIZED_EVENT_CLASS = {
        "arm_away": "ARM",
        "stay_arm": "STAY",
        "disarm": "DISARM",
        "bypass_zone": "BYPASS",
        "unbypass_zone": "UNBYPASS",
        "zone_restore": "RESTORE",
        "battery_low": "LOW_BATTERY",
        "ac_power_lost": "OFFLINE",
        "ac_power_restored": "RESTORE",
        "battery_restore": "BATTERY_OK",
        "tamper_alarm": "TAMPER",
        "peripheral_tamper": "TAMPER",
        "video_tamper": "TAMPER",
        "tamper_restore": "TAMPER_CLEAR",
        "device_online": "ONLINE",
        "device_offline": "OFFLINE",
        "zone_alarm": "ALARM",
        "panic_alarm": "ALARM",
        "medical_alarm": "ALARM",
        "fire_alarm": "ALARM",
        "fire_detection": "ALARM",
        "gas_alarm": "ALARM",
        "smart_alarm": "ALARM",
        "intrusion_detection": "ALARM",
        "io_alarm": "ALARM",
        "line_crossing": "ALARM",
        "region_entrance": "ALARM",
        "region_exit": "ALARM",
        "motion_detection": "ALARM",
        "thermal_alarm": "ALARM",
        "temperature_alarm": "ALARM",
        "temperature_difference_alarm": "ALARM",
        "manual_capture": "INFO",
        "linkage_media": "INFO",
        "disk_error": "INFO",
        "disk_full": "INFO",
        "disk_recovered": "RESTORE",
        "record_exception": "INFO",
        "video_loss": "OFFLINE",
        "system_operation": "INFO",
        "panel_power_status": "INFO",
        "panel_communication_status": "INFO",
        "zone_status": "INFO",
        "peripheral_status": "INFO",
        "panel_upgrade": "INFO",
        "intercom_call": "INFO",
        "alarm_triggered": "ALARM",
        "instant_zone_alarm": "ALARM",
        "module_added": "INFO",
        "module_removed": "INFO",
        "snapshot_captured": "INFO",
        "wired_network_fault": "OFFLINE",
        "wired_network_fault_restored": "RESTORE",
    }

    def _status_timeout(self) -> int:
        return int(getattr(settings, "HIK_PARTNER", {}).get("STATUS_TIMEOUT", 20))

    COMMAND_EVENT_META = {
        "arm": {"category": AlarmEvent.CATEGORY_ARM, "severity": AlarmEvent.SEVERITY_LOW},
        "disarm": {"category": AlarmEvent.CATEGORY_ARM, "severity": AlarmEvent.SEVERITY_LOW},
        "stay-arm": {"category": AlarmEvent.CATEGORY_ARM, "severity": AlarmEvent.SEVERITY_LOW},
        "clear-alarm": {"category": AlarmEvent.CATEGORY_SYSTEM, "severity": AlarmEvent.SEVERITY_LOW},
        "silence": {"category": AlarmEvent.CATEGORY_SYSTEM, "severity": AlarmEvent.SEVERITY_LOW},
        "panic": {"category": AlarmEvent.CATEGORY_ALARM, "severity": AlarmEvent.SEVERITY_CRITICAL},
    }

    @staticmethod
    def _normalize_event_lookup_key(value: str) -> str:
        return normalize_event_label_lookup(value)

    def __init__(self) -> None:
        self.client = HikPartnerClient()

    def health(self) -> dict:
        return {
            "configured": self.client.is_configured(),
            "base_url": self.client.base_url,
            "dry_run": self.client.dry_run,
            "delivery_mode": settings.HIK_PARTNER.get("DELIVERY_MODE", "mq"),
        }

    @staticmethod
    def get_webhook_sign_secret() -> str:
        return (
            settings.HIK_PARTNER.get("WEBHOOK_SIGN_SECRET")
            or settings.HIK_PARTNER.get("API_SECRET", "")
        )

    @staticmethod
    def get_detector_label(detector_type: str) -> str:
        """Map raw Hikvision detectorType strings to user-friendly labels."""
        return HikPartnerService.DETECTOR_TYPE_META.get(detector_type, {}).get("label", "Zone Sensor")

    @staticmethod
    def get_detector_icon(detector_type: str) -> str:
        """Map raw Hikvision detectorType strings to icon keys for the UI."""
        return HikPartnerService.DETECTOR_TYPE_META.get(detector_type, {}).get("icon", "sensor")

    @staticmethod
    def _normalize_signal_strength(signal_raw) -> str:
        if signal_raw in (None, ""):
            return ""
        if isinstance(signal_raw, str):
            normalized = signal_raw.strip()
            if normalized:
                return normalized
            return ""
        if signal_raw >= 100:
            return "strong"
        if signal_raw >= 64:
            return "middle"
        if signal_raw >= 32:
            return "weak"
        if signal_raw > 0:
            return "poor"
        return "noSignal"

    @staticmethod
    def _parse_hik_panel_datetime(raw_value) -> datetime | None:
        if raw_value in (None, ""):
            return None
        value = str(raw_value).strip()
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is not None:
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            return parsed
        for fmt in ("%d,%b,%Y %H:%M:%S", "%d,%B,%Y %H:%M:%S"):
            try:
                naive_dt = datetime.strptime(value, fmt)
                return timezone.make_aware(naive_dt, timezone.get_current_timezone())
            except ValueError:
                continue
        return None

    def _base_zone_defaults(self, zone_data: dict, *, state: str, is_online: bool, magnet_open) -> dict:
        charge_str = zone_data.get("charge", "normal")
        return {
            "name": zone_data.get("name") or f"Zone {zone_data.get('id', '')}".strip(),
            "state": state,
            "low_battery": charge_str == "lowPower",
            "charge_value": zone_data.get("chargeValue"),
            "detector_type": zone_data.get("detectorType", ""),
            "zone_type": zone_data.get("zoneType", ""),
            "reason": zone_data.get("reason", ""),
            "health_status": zone_data.get("healthStatus", ""),
            "model_number": zone_data.get("model", ""),
            "access_module_type": zone_data.get("accessModuleType", ""),
            "related_access_module_id": zone_data.get("relatedAccessModuleID"),
            "module_address": zone_data.get("address"),
            "zone_attribute": zone_data.get("zoneAttrib", ""),
            "tamper": bool(zone_data.get("tamperEvident", False)),
            "shielded": bool(zone_data.get("shielded", False)),
            "magnet_open": magnet_open if magnet_open is not None else None,
            "is_online": is_online,
            "diagnostics_result": zone_data.get("diagnosticsResult", ""),
            "network_status": zone_data.get("networkStatus", ""),
            "external_power": zone_data.get("externalPower", ""),
            "main_charge": zone_data.get("mainCharge", ""),
            "preheat_status": zone_data.get("preheatStatus", ""),
            "useful_life_status": zone_data.get("userfulLifeStatus") or zone_data.get("usefulLifeStatus", ""),
            "maze_status": zone_data.get("mazeStatus", ""),
            "sensor_status": zone_data.get("sensorStatus", ""),
            "temperature": zone_data.get("temperature"),
            "humidity": zone_data.get("humidity"),
        }

    def _sync_peripheral_inventory(self, *, site: Site, panel: AlarmPanelDevice, alarm_status: dict, now: datetime | None = None) -> int:
        now = now or timezone.now()
        synced = 0
        peripheral_map = (
            (AlarmPeripheral.TYPE_KEYPAD, "keyPadList"),
            (AlarmPeripheral.TYPE_KEYFOB, "remoteList"),
            (AlarmPeripheral.TYPE_CARD_READER, "cardReaderList"),
            (AlarmPeripheral.TYPE_OUTPUT_MODULE, "outPutList"),
            (AlarmPeripheral.TYPE_REPEATER, "repeaterList"),
            (AlarmPeripheral.TYPE_SIREN, "sirenList"),
            (AlarmPeripheral.TYPE_TRANSMITTER, "TransmitterList"),
        )
        touched_ids = []

        for peripheral_type, list_key in peripheral_map:
            for item in alarm_status.get(list_key, []) or []:
                item_id = item.get("id")
                if item_id is None:
                    continue
                defaults = {
                    "site": site,
                    "name": item.get("name", f"{peripheral_type.replace('_', ' ').title()} {item_id}"),
                    "serial_number": item.get("seq", ""),
                    "peripheral_type_label": item.get("peripheralType", ""),
                    "diagnostics_result": item.get("diagnosticsResult", ""),
                    "network_status": item.get("networkStatus", ""),
                    "battery_status": item.get("batteryStatus", ""),
                    "signal_strength": self._normalize_signal_strength(item.get("signalStrength")),
                    "tamper": str(item.get("tamperStatus", "false")).lower() == "true",
                    "bypassed": str(item.get("byPassStatus", "No")).lower() == "yes",
                    "external_power": item.get("externalPower", ""),
                    "is_online": item.get("networkStatus", "").lower() not in {"offline", "disconnect", "disconnected"},
                    "last_seen_at": now,
                    "last_operation_at": self._parse_hik_panel_datetime(item.get("lastOperationTime")),
                    "last_triggered_at": self._parse_hik_panel_datetime(item.get("lastTriggerTime") or item.get("lastSoundTime")),
                    "metadata": {k: v for k, v in item.items() if k not in {"id", "name", "seq", "peripheralType", "diagnosticsResult", "networkStatus", "batteryStatus", "signalStrength", "tamperStatus", "byPassStatus", "externalPower", "lastOperationTime", "lastTriggerTime", "lastSoundTime"}},
                }
                peripheral, _ = AlarmPeripheral.objects.update_or_create(
                    device=panel,
                    peripheral_type=peripheral_type,
                    peripheral_number=item_id,
                    defaults=defaults,
                )
                touched_ids.append(peripheral.id)
                synced += 1

                if peripheral_type in {
                    AlarmPeripheral.TYPE_KEYPAD,
                    AlarmPeripheral.TYPE_KEYFOB,
                    AlarmPeripheral.TYPE_CARD_READER,
                }:
                    subsystem = panel.subsystems.order_by("subsystem_number").first()
                    if subsystem:
                        Zone.objects.update_or_create(
                            subsystem=subsystem,
                            zone_number=item_id,
                            device_type={
                                AlarmPeripheral.TYPE_KEYPAD: Zone.DEVICE_TYPE_KEYPAD,
                                AlarmPeripheral.TYPE_KEYFOB: Zone.DEVICE_TYPE_KEYFOB,
                                AlarmPeripheral.TYPE_CARD_READER: Zone.DEVICE_TYPE_CARD_READER,
                            }[peripheral_type],
                            defaults={
                                "name": defaults["name"],
                                "low_battery": defaults["battery_status"].lower() == "low",
                                "signal_strength": defaults["signal_strength"],
                                "tamper": defaults["tamper"],
                                "is_online": defaults["is_online"],
                                "last_seen_at": now,
                                "network_status": defaults["network_status"],
                                "diagnostics_result": defaults["diagnostics_result"],
                            },
                        )

        AlarmPeripheral.objects.filter(device=panel).exclude(id__in=touched_ids).delete()
        return synced

    def _resolve_panel_power_status(
        self,
        *,
        panel: AlarmPanelDevice,
        alarm_status: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        normalized = AlarmPanelDevice.normalize_battery_status_value(
            (alarm_status or {}).get("batteryStatus")
        )
        if normalized != AlarmPanelDevice.BATTERY_UNKNOWN:
            return normalized

        if panel.is_online:
            try:
                health_resp = self.client.transparent(
                    device_serial=panel.serial_number,
                    method="GET",
                    isapi_uri="/ISAPI/SecurityCP/status/hostHealth?format=json",
                    headers=headers or {"X-Userlevel": "1"},
                    timeout=min(self._status_timeout(), 20),
                )
                power_raw = (health_resp or {}).get("HostHealth", {}).get("powerStatus")
                normalized = AlarmPanelDevice.normalize_battery_status_value(power_raw)
                if normalized != AlarmPanelDevice.BATTERY_UNKNOWN:
                    return normalized
            except Exception:
                logger.debug(
                    "_resolve_panel_power_status: hostHealth unavailable for %s",
                    panel.serial_number,
                )

        if AlarmPanelDevice.normalize_battery_status_value(panel.battery_status) != AlarmPanelDevice.BATTERY_UNKNOWN:
            return AlarmPanelDevice.normalize_battery_status_value(panel.battery_status)
        return AlarmPanelDevice.BATTERY_UNKNOWN

    def _sync_outputs_via_isapi(self, panel: AlarmPanelDevice) -> int:
        try:
            resp = self.client.transparent(
                device_serial=panel.serial_number,
                method="POST",
                isapi_uri="/ISAPI/SecurityCP/status/outputStatus?format=json",
                body={"OutputCond": {"searchID": f"securehub-{panel.serial_number}", "searchResultPosition": 0, "maxResults": 200}},
                headers={"X-Userlevel": "1"},
                timeout=self._status_timeout(),
            )
        except Exception as exc:
            logger.warning("_sync_outputs_via_isapi: failed for %s: %s", panel.serial_number, exc)
            return 0

        output_list = ((resp or {}).get("OutputSearch") or {}).get("OutputList") or []
        touched_ids = []
        synced = 0
        for entry in output_list:
            output = entry.get("Output", {})
            output_id = output.get("id")
            if output_id is None:
                continue
            signal_strength = self._normalize_signal_strength(output.get("signal"))
            status = output.get("status", "")
            obj, _ = AlarmOutput.objects.update_or_create(
                device=panel,
                output_number=output_id,
                defaults={
                    "site": panel.site,
                    "name": output.get("name", f"Output {output_id}"),
                    "status": status,
                    "tamper": bool(output.get("tamperEvident", False)),
                    "battery_status": output.get("charge", ""),
                    "signal_strength": signal_strength,
                    "linkage": output.get("linkage", ""),
                    "duration_const_output_enable": bool(output.get("durationConstOutputEnable", False)),
                    "is_available": output.get("isAvailable", True),
                    "access_module_type": output.get("accessModuleType", ""),
                    "related_access_module_id": output.get("relatedAccessModuleID"),
                    "module_address": output.get("address"),
                    "subsystem_numbers": output.get("subSystemList", []) or [],
                    "scenario_types": output.get("scenarioType", []) or [],
                    "relay_attribute": output.get("relayAttrib", ""),
                    "device_number": output.get("deviceNo"),
                    "model_number": output.get("devName", ""),
                    "diagnostics_result": output.get("diagnosticsResult", ""),
                    "network_status": "",
                    "is_online": status not in {AlarmOutput.STATUS_OFFLINE, AlarmOutput.STATUS_HEARTBEAT_ABNORMAL},
                    "serial_number": output.get("devIndex", ""),
                },
            )
            touched_ids.append(obj.id)
            synced += 1

        AlarmOutput.objects.filter(device=panel).exclude(id__in=touched_ids).delete()
        return synced

    @staticmethod
    def _clean_text(value) -> str:
        return str(value or "").strip()

    def _build_geocode_queries(self, site: Site) -> list[str]:
        queries = []
        address_only = ", ".join(
            part for part in [self._clean_text(site.address), self._clean_text(site.city), self._clean_text(site.state)] if part
        )
        if address_only:
            queries.append(address_only)
        name_plus_address = ", ".join(
            part for part in [self._clean_text(site.name), self._clean_text(site.address), self._clean_text(site.city), self._clean_text(site.state)] if part
        )
        if name_plus_address and name_plus_address not in queries:
            queries.append(name_plus_address)
        return queries

    def geocode_site_location(self, site: Site, *, force: bool = False) -> bool:
        geocoding_cfg = getattr(settings, "SITE_GEOCODING", {})
        if not geocoding_cfg.get("ENABLED", True):
            return False
        if site.latitude is not None and site.longitude is not None and not force:
            return False

        headers = {"User-Agent": geocoding_cfg.get("USER_AGENT", "securehub/1.0")}
        timeout = geocoding_cfg.get("TIMEOUT", 10)
        url = geocoding_cfg.get("URL", "https://nominatim.openstreetmap.org/search")

        for query in self._build_geocode_queries(site):
            try:
                response = requests.get(
                    url,
                    params={"q": query, "format": "jsonv2", "limit": 1},
                    headers=headers,
                    timeout=timeout,
                )
                response.raise_for_status()
                results = response.json() or []
            except Exception as exc:
                logger.warning("geocode_site_location: failed for site %s: %s", site.name, exc)
                return False

            if not results:
                continue

            row = results[0]
            try:
                site.latitude = Decimal(str(row["lat"]))
                site.longitude = Decimal(str(row["lon"]))
            except (KeyError, InvalidOperation, TypeError) as exc:
                logger.warning("geocode_site_location: invalid coordinates for site %s: %s", site.name, exc)
                return False

            site.save(update_fields=["latitude", "longitude", "updated_at"])
            logger.info("geocode_site_location: resolved coordinates for site %s", site.name)
            return True

        logger.info("geocode_site_location: no coordinates found for site %s", site.name)
        return False

    def _find_site_search_row(
        self,
        site: Site,
        *,
        device_list: list[dict] | None = None,
    ) -> dict | None:
        search_terms = []
        if self._clean_text(site.name):
            search_terms.append(self._clean_text(site.name))
        for device in device_list or []:
            if device.get("siteID") != site.hik_site_id:
                continue
            site_name = self._clean_text(device.get("siteName"))
            if site_name and site_name not in search_terms:
                search_terms.append(site_name)
        search_terms.append("")

        for term in search_terms:
            page = 1
            while page <= 5:
                resp = self.client.search_sites(search=term, page=page, page_size=100)
                data = resp.get("data", {}) or {}
                rows = data.get("rows", []) or []
                if not rows and term:
                    break
                for row in rows:
                    if row.get("id") == site.hik_site_id:
                        return row
                total = int(data.get("total") or 0)
                if total and page * 100 >= total:
                    break
                if len(rows) < 100:
                    break
                page += 1
        return None

    def _apply_site_hints_from_devices(self, site: Site, device_list: list[dict] | None) -> bool:
        for device in device_list or []:
            if device.get("siteID") != site.hik_site_id:
                continue

            update_fields = []
            site_name = self._clean_text(device.get("siteName"))
            if site_name and site.name != site_name:
                site.name = site_name
                update_fields.append("name")

            time_zone = self._clean_text(device.get("timeZone"))
            if time_zone and site.timezone != time_zone:
                site.timezone = time_zone
                update_fields.append("timezone")

            if update_fields:
                update_fields.append("updated_at")
                site.save(update_fields=update_fields)
                logger.info("sync_site_metadata: applied device-list metadata for site %s", site.hik_site_id)
                return True

        return False

    def sync_alarm_status(self, site: Site) -> None:
        """
        Pull live partition and zone state from each alarm panel device via transparent ISAPI
        and write the results into the local Subsystem and Zone models.

        Partition status — GET /ISAPI/SecurityCP/status/subSystems?format=json
          Response: JSON_SubSysList (§A.5.9)
            SubSys.id       — partition number (starts from 1)
            SubSys.arming   — "stay" | "away" | "disarm" | "arming"
            SubSys.alarm    — boolean, true = alarm triggered

        Zone status — GET /ISAPI/SecurityCP/status/zones?format=json
          Response: JSON_ZoneList (§A.5.13)
            Zone.id         — zone number
            Zone.alarm      — boolean
            Zone.bypassed   — boolean
            Zone.status     — "online" | "offline" | "trigger" | "notRelated" | …
        """
        if self.client.dry_run:
            return

        # Mapping from ISAPI arming string to local model status
        _arming_to_status = {
            "stay": Subsystem.STATUS_STAY,
            "away": Subsystem.STATUS_ARMED,
            "arming": Subsystem.STATUS_ARMED,
            "disarm": Subsystem.STATUS_DISARMED,
        }
        
        for device in site.devices.all():
            if not device.is_online:
                logger.info("sync_alarm_status: skipping offline device %s", device.serial_number)
                continue

            # Fetch detailed identity (firmware/hardware) occasionally or if missing
            self._sync_device_identity(device)

            # ----- Partitions -----
            # Per API guide §3.23: X-Userlevel=1 (Admin/Operator) is often required for 
            # AX Pro panels even on read-only transparent ISAPI calls.
            ax_pro_headers = {"X-Userlevel": "1"}
            partition_statuses = []
            try:
                resp = self.client.transparent(
                    device_serial=device.serial_number,
                    method="GET",
                    isapi_uri="/ISAPI/SecurityCP/status/subSystems?format=json",
                    headers=ax_pro_headers,
                    timeout=self._status_timeout(),
                )
                enabled_partition_ids = []
                for entry in resp.get("SubSysList", []):
                    sub = entry.get("SubSys", {})
                    partition_no = sub.get("id")
                    # B2 FIX: `enabled` is optional per §A.5.9 — treat None as True (enabled).
                    # Using truthiness caused all partitions to be skipped when firmware
                    # omits the field. Only skip when explicitly set to False.
                    if partition_no is None or sub.get("enabled") is False:
                        continue
                    
                    enabled_partition_ids.append(partition_no)
                    sub_name = sub.get("name", f"Area {partition_no}")
                    if sub.get("alarm"):
                        new_status = Subsystem.STATUS_ALARM
                    else:
                        new_status = _arming_to_status.get(
                            sub.get("arming", "disarm"), Subsystem.STATUS_DISARMED
                        )
                    
                    partition_statuses.append(new_status)
                    
                    # E2: capture remaining delay per §A.5.9 SubSys.delayTime
                    delay_time = sub.get("delayTime")  # seconds; valid when arming/stay

                    Subsystem.objects.update_or_create(
                        device=device,
                        subsystem_number=partition_no,
                        defaults={
                            "name": sub_name,
                            "hik_subsystem_id": f"{device.serial_number}_{partition_no}",
                            "status": new_status,
                            "delay_time_remaining": delay_time,
                            "site": site,
                        }
                    )
                
                # Optional: Delete subsystems that are no longer enabled
                Subsystem.objects.filter(device=device).exclude(
                    subsystem_number__in=enabled_partition_ids
                ).delete()
                # ----- Update Aggregate Panel Status -----
                # Update last sync time and battery status
                device.last_health_check = timezone.now()
                
                # Fetch detailed host health (AC Power / Battery status)
                try:
                    device.battery_status = self._resolve_panel_power_status(
                        panel=device,
                        headers=ax_pro_headers,
                    )
                except Exception as health_exc:
                    logger.debug("sync_alarm_status: hostHealth failed for %s", device.serial_number)
                    # Fallback stays "OK" for now or stays as previously reported
                
                # Determine aggregate mode
                if partition_statuses:
                    if Subsystem.STATUS_ALARM in partition_statuses:
                        device.work_status = AlarmPanelDevice.WORK_ALARM
                    elif all(s == Subsystem.STATUS_DISARMED for s in partition_statuses):
                        device.work_status = AlarmPanelDevice.WORK_DISARMED
                    elif any(s == Subsystem.STATUS_STAY for s in partition_statuses):
                        device.work_status = AlarmPanelDevice.WORK_PART_ARM
                    else:
                        device.work_status = AlarmPanelDevice.WORK_ARMED
                else:
                    device.work_status = AlarmPanelDevice.WORK_UNKNOWN

                device.save(update_fields=["last_health_check", "battery_status", "work_status", "updated_at"])

            except Exception as exc:
                logger.warning(
                    "sync_alarm_status: sync failed for %s: %s",
                    device.serial_number,
                    exc,
                )
                # DO NOT update last_health_check or battery_status if sync failed!
                # This prevents "False Positive" statuses when the connection is broken.

            # ----- Zones -----
            try:
                resp = self.client.transparent(
                    device_serial=device.serial_number,
                    method="GET",
                    isapi_uri="/ISAPI/SecurityCP/status/zones?format=json",
                    headers=ax_pro_headers,
                    timeout=self._status_timeout(),
                )
                touched_zone_ids = []
                for entry in resp.get("ZoneList", []):
                    zone_data = entry.get("Zone", {})
                    zone_no = zone_data.get("id")  # 0-indexed sequential id in the ZoneList
                    if zone_no is None:
                        continue

                    # Skip zones that are not enrolled in any partition
                    if zone_data.get("status") == "notRelated":
                        continue

                    # subSystemNo: the partition this zone belongs to (1-indexed)
                    sub_no = zone_data.get("subSystemNo", 1)
                    subsystem = Subsystem.objects.filter(device=device, subsystem_number=sub_no).first()
                    if subsystem is None:
                        subsystem, _ = Subsystem.objects.get_or_create(
                            device=device,
                            subsystem_number=sub_no,
                            defaults={
                                "name": f"Area {sub_no}",
                                "hik_subsystem_id": f"{device.serial_number}_{sub_no}",
                                "status": Subsystem.STATUS_DISARMED,
                                "site": site,
                            },
                        )

                    # Determine zone state
                    # magnetOpenStatus: True = contact sensor is open (door/window open)
                    magnet_open = zone_data.get("magnetOpenStatus")
                    is_disarmed = subsystem and subsystem.status == Subsystem.STATUS_DISARMED
                    
                    if zone_data.get("alarm"):
                        new_state = Zone.STATE_ALARM
                    elif zone_data.get("bypassed"):
                        new_state = Zone.STATE_BYPASSED
                    elif zone_data.get("status") == "trigger":
                        # If the system is disarmed, "trigger" on a contact usually means "Open"
                        new_state = Zone.STATE_OPEN if is_disarmed else Zone.STATE_ALARM
                    elif magnet_open is True:
                        new_state = Zone.STATE_OPEN
                    else:
                        new_state = Zone.STATE_NORMAL

                    # deviceNo: actual panel enrollment slot number (matches Hik-Partner display)
                    device_no = zone_data.get("deviceNo")
                    # Zone.status == "online" confirms device connectivity
                    is_online = zone_data.get("status") != "offline"

                    defaults = self._base_zone_defaults(
                        zone_data,
                        state=new_state,
                        is_online=is_online,
                        magnet_open=magnet_open,
                    )
                    signal_str = self._normalize_signal_strength(zone_data.get("signal"))
                    if signal_str:
                        defaults["signal_strength"] = signal_str
                    if device_no is not None:
                        defaults["device_number"] = device_no

                    zone_obj, _ = Zone.objects.update_or_create(
                        subsystem=subsystem,
                        zone_number=zone_no,
                        device_type=Zone.DEVICE_TYPE_ZONE,
                        defaults=defaults,
                    )
                    touched_zone_ids.append(zone_obj.id)

                # Remove stale zone records for this device (e.g. zone moved subsystem)
                Zone.objects.filter(
                    subsystem__device=device,
                    device_type=Zone.DEVICE_TYPE_ZONE,
                ).exclude(id__in=touched_zone_ids).delete()
                self._sync_outputs_via_isapi(device)
            except Exception as exc:
                logger.warning(
                    "sync_alarm_status: zone sync failed for %s: %s",
                    device.serial_number,
                    exc,
                )

    def _sync_device_identity(self, device: AlarmPanelDevice, force: bool = False) -> None:
        """
        Fetch firmware and hardware versions via transparent ISAPI /ISAPI/System/deviceInfo.
        Implementation follows 'fetch once, refresh occasionally' pattern.
        """
        # Only refresh if fields are empty, or if specifically forced
        has_identity = device.firmware_version and device.hardware_version and device.model_number
        if has_identity and not force:
            # Refresh occasionally? For now, we stick to 'fetch once' if already present
            # to minimize ISAPI overhead on every 2-minute sync.
            return

        logger.debug("Fetching device identity for %s via ISAPI", device.serial_number)
        try:
            resp = self.client.transparent(
                device_serial=device.serial_number,
                method="GET",
                isapi_uri="/ISAPI/System/deviceInfo?format=json",
                headers={"X-Userlevel": "1"},
                timeout=min(self._status_timeout(), 20),
            )
            
            info = {}
            if isinstance(resp, dict):
                info = resp.get("DeviceInfo", {})
            elif isinstance(resp, str):
                # Handle XML response
                try:
                    root = ET.fromstring(resp)
                    # Strip namespace if present
                    if "}" in root.tag:
                        ns = root.tag.split("}")[0].strip("{")
                        for child in root:
                            tag = child.tag.split("}")[-1]
                            info[tag] = child.text
                    else:
                        for child in root:
                            info[child.tag] = child.text
                except ET.ParseError as exc:
                    logger.error("Failed to parse identity XML for %s: %s", device.serial_number, exc)
                    return

            if not info:
                logger.warning("Empty identity info for %s", device.serial_number)
                return

            # Robust mapping with fallbacks
            model = info.get("model") or info.get("deviceModel") or info.get("modelNumber")
            fw = info.get("firmwareVersion") or info.get("softwareVersion") or info.get("firmwareRev")
            hw = info.get("hardwareVersion") or info.get("hardwareRev") or info.get("encoderVersion")

            device.model_number = model if model else device.model_number
            device.firmware_version = fw if fw else device.firmware_version
            device.hardware_version = hw if hw else device.hardware_version
            
            device.save(update_fields=["model_number", "firmware_version", "hardware_version", "updated_at"])
            logger.info(
                "Updated identity for %s: model=%s, fw=%s, hw=%s",
                device.serial_number, device.model_number, device.firmware_version, device.hardware_version
            )
        except Exception as exc:
            logger.warning("Failed to fetch device identity for %s: %s", device.serial_number, exc)

    def get_site_status(self, site: Site) -> dict:
        subsystems = list(site.subsystems.prefetch_related("zones").all())
        armed_states = {Subsystem.STATUS_ARMED, Subsystem.STATUS_STAY, Subsystem.STATUS_ALARM}
        active_alarm_count = sum(1 for item in subsystems if item.status == Subsystem.STATUS_ALARM)
        return {
            "site_id": site.id,
            "armed_subsystems": sum(1 for item in subsystems if item.status in armed_states),
            "disarmed_subsystems": sum(
                1 for item in subsystems if item.status == Subsystem.STATUS_DISARMED
            ),
            "active_alarm_count": active_alarm_count,
            "offline_device_count": site.devices.filter(is_online=False).count(),
            "subsystems": subsystems,
        }

    def sync_site_metadata(self, site: Site, *, device_list: list[dict] | None = None) -> None:
        """
        Fetch granular site metadata (State, City, Address, Industry) from Hik-Partner Pro
        and update the local Site record.
        """
        if self.client.dry_run:
            logger.debug("sync_site_metadata: dry run, skipping")
            return

        try:
            site_info = self._find_site_search_row(site, device_list=device_list)
            if not site_info:
                logger.warning("sync_site_metadata: Site %s not found in search results", site.hik_site_id)
                self._apply_site_hints_from_devices(site, device_list)
                return

            site.name = site_info.get("siteName") or site.name
            site.state = site_info.get("siteState") or site.state
            site.city = site_info.get("siteCity") or site.city
            site.timezone = site_info.get("timeZone") or site.timezone
            site.address = (
                self._clean_text(site_info.get("location"))
                or self._clean_text(site_info.get("siteStreet"))
                or site.address
            )

            primary = site_info.get("primaryIndustry") or site_info.get("industryType")
            secondary = site_info.get("secondaryIndustry")
            if primary:
                site.primary_industry = normalize_scene_label(primary)
            if secondary:
                site.secondary_industry = secondary

            site.save(update_fields=["name", "state", "city", "address", "timezone", "primary_industry", "secondary_industry", "updated_at"])
            self.geocode_site_location(site)
            logger.info("sync_site_metadata: Updated metadata for site %s", site.name)
            
        except Exception as exc:
            logger.warning("sync_site_metadata: Failed for site %s: %s", site.name, exc)
            self._apply_site_hints_from_devices(site, device_list)

    def sync_site_devices(self, site: Site):
        """
        Synchronize local AlarmPanelDevice models with Hik-Partner Pro.

        Device category mapping per API guide §3.21:
          3  = AlarmHost (AX Pro / DS-series alarm panel) ← only confirmed panel category
          Sub-categories (deviceSubCategory) for category-3:
            3=AX2, 4=AX Hub, 5=AX Hybrid, 10=AX Hybrid Pro

        AlarmPanelDevice records are created for every device whose category matches
        the known alarm panel sets, so that arm/disarm and sync_alarm_status work
        without requiring manual registration.
        """

        ALARM_PANEL_CATEGORIES = {3}
        # serials of alarm panels already registered for this site
        known_panel_serials = set(
            AlarmPanelDevice.objects.filter(site=site)
            .values_list("serial_number", flat=True)
        )

        if self.client.dry_run:
            # Mock sync: Demo AX Pro panel
            AlarmPanelDevice.objects.update_or_create(
                hik_device_id="demo-panel-001",
                defaults={
                    "site": site,
                    "name": "Demo AX Pro",
                    "model_number": "DS-PWA96-M-WE",
                    "serial_number": "DEMO-SN-AXPRO",
                    "device_type": AlarmPanelDevice.DEVICE_TYPE_PANEL,
                    "hik_device_sub_category": 3,  # AX2 sub-category
                    "is_online": True,
                },
            )
            return {"synced_panels": 1}

        # Real API — Per guide §3.21: POST /api/hpcgw/v1/device/list.
        # Production sites can exceed the API default page size, so collect all
        # pages before registering local panels/subscriptions.
        device_list = self._fetch_site_device_list(site.hik_site_id)
        
        # Also sync site metadata (State, Scene, etc.)
        self.sync_site_metadata(site, device_list=device_list)

        synced_panels = 0
        touched_hik_device_ids = []

        for dev_info in device_list:
            dev_id = dev_info["id"]
            dev_serial = dev_info.get("deviceSerial", "")
            dev_name = dev_info.get("deviceName", "Unknown Device")
            dev_model = dev_info.get("deviceModel", "")
            dev_category = dev_info.get("deviceCategory", 0)
            dev_sub_category = dev_info.get("deviceSubCategory")
            # deviceOnlineStatus: 0=offline, 1=online, 2=unknown
            is_online = dev_info.get("deviceOnlineStatus") == 1
            touched_hik_device_ids.append(dev_id)

            HikSiteDevice.objects.update_or_create(
                hik_device_id=dev_id,
                defaults={
                    "site": site,
                    "name": dev_name,
                    "serial_number": dev_serial,
                    "device_category": dev_category,
                    "device_sub_category": dev_sub_category,
                    "device_type": dev_info.get("deviceType", "") or dev_info.get("deviceModel", ""),
                    "device_version": dev_info.get("deviceVersion", ""),
                    "is_online": is_online,
                    "is_subscribed": bool(dev_info.get("isSubscribed")),
                    "raw_payload": dev_info,
                },
            )

            # Determine if this device should be treated as an alarm panel:
            # - explicit alarm panel category (AlarmHost = 3 per spec §3.21), OR
            # - serial is already registered as an alarm panel (e.g. manually via Register form)
            is_panel = dev_category in ALARM_PANEL_CATEGORIES or dev_serial in known_panel_serials

            if not is_panel:
                logger.debug("sync_site_devices: skipping non-panel device %s (category=%s)", dev_serial, dev_category)
                continue

            # ---- Alarm panel / security host (AX Pro, DS-series panel, etc.) ----
            _, created = AlarmPanelDevice.objects.update_or_create(
                hik_device_id=dev_id,
                defaults={
                    "site": site,
                    "name": dev_name,
                    "model_number": dev_model,
                    "serial_number": dev_serial,
                    "device_type": AlarmPanelDevice.DEVICE_TYPE_PANEL,
                    "hik_device_sub_category": dev_sub_category,
                    "is_online": is_online,
                },
            )
            if created:
                synced_panels += 1
                logger.info(
                    "sync_site_devices: registered alarm panel '%s' (serial=%s, category=%s, sub=%s) "
                    "for site '%s'",
                    dev_name, dev_serial, dev_category, dev_sub_category, site.name,
                )

        if touched_hik_device_ids:
            HikSiteDevice.objects.filter(site=site).exclude(
                hik_device_id__in=touched_hik_device_ids
            ).delete()

        # Subscribe to MQ events for all devices (panels)
        all_serials = [d.get("deviceSerial") for d in device_list if d.get("deviceSerial")]
        if all_serials:
            try:
                self.client.subscribe_events(all_serials)
            except Exception as exc:
                logger.warning("sync_site_devices: subscribe_events failed: %s", exc)

        return {
            "synced_panels": synced_panels,
            "devices_seen": len(device_list),
        }

    def _fetch_site_device_list(self, hik_site_id: str, *, page_size: int = 100) -> list[dict]:
        rows: list[dict] = []
        page = 1

        while True:
            devices_data = self.client.list_devices(
                site_id=hik_site_id,
                page=page,
                page_size=page_size,
            )
            data = devices_data.get("data", {}) or {}
            page_rows = data.get("rows", []) or []
            rows.extend(page_rows)

            total = int(data.get("total") or 0)
            if total:
                if len(rows) >= total or not page_rows:
                    break
            elif len(page_rows) < page_size:
                break
            page += 1

        return rows

    def resubscribe_all_sites(self) -> dict:
        """
        Re-establish MQ event subscriptions for every active site.
        This is used to recover from LAP068001 (not subscribed) errors.
        """
        sites = Site.objects.filter(is_active=True).exclude(hik_site_id="")
        subscribed = errors = 0
        
        # Collect all serial numbers from all active sites
        for site in sites:
            try:
                # Re-sync devices to get current serials and trigger subscription
                result = self.sync_site_devices(site)
                subscribed += result.get("synced_panels", 0)
            except Exception as exc:
                logger.warning("resubscribe_all_sites: failed for site %s: %s", site.name, exc)
                errors += 1
                
        return {"sites_processed": sites.count(), "errors": errors}

    def execute_subsystem_command(
        self, site: Site, subsystem: Subsystem, action: str, 
        payload: dict = None, requesting_user=None
    ) -> dict:
        if action not in {"arm", "disarm", "stay-arm", "clear-alarm", "silence", "panic"}:
            raise HikPartnerError(f"Unsupported action: {action}")
        
        target_status = {
            "arm": Subsystem.STATUS_ARMED,
            "disarm": Subsystem.STATUS_DISARMED,
            "stay-arm": Subsystem.STATUS_STAY,
            "clear-alarm": Subsystem.STATUS_DISARMED,
            "silence": subsystem.status,
            "panic": Subsystem.STATUS_ALARM,
        }[action]

        isapi_uri = self._map_action_to_isapi(subsystem=subsystem, action=action)

        # Per API guide §3.23: X-Userlevel is required for AX Pro control.
        # 0 = Installer (default for partner cloud access), 1 = Admin/Operator.
        # If no operator username is provided, we must use level 0 to avoid "User Not Exist" errors (0x4000804F).
        payload = payload or {}
        operator_username = payload.get("operator_username")
        ax_pro_headers = {"X-Userlevel": "1" if operator_username else "0"}
        
        if operator_username:
            ax_pro_headers["X-Username"] = operator_username
            if payload.get("operator_password"):
                ax_pro_headers["X-Password"] = payload["operator_password"]

        request_body = {"Operate": {}}
        module_operate_code = payload.get("moduleOperateCode")
        if module_operate_code:
            request_body["Operate"]["moduleOperateCode"] = module_operate_code


        # Perform the actual request if not in dry run
        api_response = {}
        if not self.client.dry_run:
            try:
                api_response = self.client.transparent(
                    device_serial=subsystem.device.serial_number,
                    method="PUT",
                    isapi_uri=isapi_uri,
                    body=request_body,
                    headers=ax_pro_headers,
                    timeout=30,
                )
                logger.debug(
                    "HikPartner API response for %s: %s", action, api_response
                )
            except HikPartnerError as e:
                # 0x40200A0B (1073774603): panel reports armedStatus conflict —
                # the partition is already in the requested state (e.g. armed via
                # keyfob before the app command arrived). Treat as idempotent
                # success so the local DB status converges with the panel.
                if e.error_code == "1073774603" and action in {"arm", "stay-arm", "disarm"}:
                    logger.warning(
                        "Panel already in target state for %s (0x40200A0B) — treating as success",
                        action,
                    )
                    api_response = {"idempotent": True, "error_code": e.error_code}
                elif e.error_code == "LAP020011":
                    subsystem.device.is_online = False
                    subsystem.device.save(update_fields=["is_online", "updated_at"])
                    logger.warning(
                        "Panel %s marked offline after Hik rejected %s command as unreachable",
                        subsystem.device.serial_number,
                        action,
                    )
                    raise HikPartnerError(
                        "Panel is offline or unreachable. Refresh status after the panel reconnects.",
                        error_code=e.error_code,
                        payload=e.payload,
                        status_code=e.status_code,
                    )
                else:
                    logger.error("HikPartner API request failed: %s", e, exc_info=True)
                    raise HikPartnerError(
                        f"Failed to execute command on Hik-Partner Pro: {e}",
                        error_code=e.error_code,
                        payload=e.payload,
                        status_code=e.status_code,
                    )
            except Exception as e:
                logger.error("HikPartner API request failed: %s", e, exc_info=True)
                raise HikPartnerError(f"Failed to execute command on Hik-Partner Pro: {e}")

        subsystem.status = target_status
        subsystem.save(update_fields=["status", "updated_at"])


        # Strip sensitive credentials before persisting the event payload
        safe_payload = {**payload} if payload else {}
        if safe_payload.get("operator_password"):
            safe_payload["operator_password"] = "***"

        event_type = self._event_type_for_action(action)
        performed_by = ""
        if requesting_user:
            performed_by = requesting_user.get_full_name() or requesting_user.username

        event = AlarmEvent.objects.create(
            site=site,
            subsystem=subsystem,
            event_type=event_type,
            event_code=action,
            performed_by=performed_by,
            event_category=self.COMMAND_EVENT_META[action]["category"],
            severity=self.COMMAND_EVENT_META[action]["severity"],
            payload={
                "event_name": humanize_event_label(event_type),
                "normalized_event_type": event_type,
                "action": action,
                "requested_payload": safe_payload,
                "isapi_uri": isapi_uri,
                "api_response": api_response,
                "dry_run": self.client.dry_run,
            },
            occurred_at=timezone.now(),
        )

        # Trigger notification dispatch for command-based events immediately 
        # (Handles console actions and app-initiated commands)
        from apps.alarms.tasks import dispatch_alarm_notifications
        dispatch_alarm_notifications.delay(str(event.id))

        return {
            "event_id": str(event.id),
            "queued": True,
            "dry_run": self.client.dry_run,
            "site_id": str(site.id),
            "subsystem_id": str(subsystem.id),
            "hik_subsystem_id": subsystem.hik_subsystem_id,
            "action": action,
            "isapi_uri": isapi_uri,
            # Store non-sensitive transparent request info for audit purposes
            "transparent_request": {
                "headers": {"X-Devserial": subsystem.device.serial_number},
            },
            "api_response": api_response,
        }

    def get_panel_control_capabilities(self, panel: AlarmPanelDevice) -> dict:
        try:
            return self.client.transparent(
                device_serial=panel.serial_number,
                method="GET",
                isapi_uri="/ISAPI/SecurityCP/control/capabilities?format=json",
                timeout=20,
            ).get("HostControlCap", {})
        except HikPartnerError as exc:
            logger.warning(
                "get_panel_control_capabilities: panel %s unavailable: %s",
                panel.serial_number,
                exc,
            )
            return {}

    def get_site_panic_capability(self, site: Site) -> dict:
        online_panels = []
        one_key_alarm_panels = 0
        unknown_panels = 0

        for panel in AlarmPanelDevice.objects.filter(site=site, is_online=True).prefetch_related("subsystems"):
            if not panel.subsystems.exists():
                continue
            control_cap = self.get_panel_control_capabilities(panel)
            supports_one_key_alarm = bool(control_cap.get("isSptOneKeyAlarmCtrl"))
            if supports_one_key_alarm:
                one_key_alarm_panels += 1
                mode = "one_key_alarm"
            elif control_cap:
                mode = "partition_fallback"
            else:
                unknown_panels += 1
                mode = "unknown"
            online_panels.append(
                {
                    "panel": panel.serial_number,
                    "mode": mode,
                    "supports_one_key_alarm": supports_one_key_alarm,
                }
            )

        if not online_panels:
            return {
                "audible_enabled": False,
                "silent_enabled": False,
                "mode": "unavailable",
                "summary_message": "No online panels are available for panic dispatch.",
                "panels": [],
            }

        if one_key_alarm_panels:
            if one_key_alarm_panels == len(online_panels):
                summary_message = "This site supports audible panic only through Hik-Partner Pro."
            else:
                summary_message = "Some online panels support audible panic only, so silent panic is unavailable site-wide."
            return {
                "audible_enabled": True,
                "silent_enabled": False,
                "mode": "one_key_alarm",
                "summary_message": summary_message,
                "panels": online_panels,
            }

        if unknown_panels:
            return {
                "audible_enabled": True,
                "silent_enabled": False,
                "mode": "unknown",
                "summary_message": "Audible panic is available, but silent panic could not be confirmed for this site.",
                "panels": online_panels,
            }

        return {
            "audible_enabled": True,
            "silent_enabled": True,
            "mode": "partition_fallback",
            "summary_message": "Audible and silent panic are available for this site.",
            "panels": online_panels,
        }

    def trigger_global_panic(self, site: Site, panic_type: str = "audible") -> dict:
        """
        Trigger a panic alarm across all subsystems on all panels associated with the site.
        panic_type: "audible" (siren fires) or "silent" (no siren, ARC-only notification).
        Per ISAPI §A.4: body {"Operate": {"alarmType": "audible"|"silent"}}.
        Each partition is addressed individually using the per-subsystem panicAlarm URI.
        """
        if panic_type not in {"audible", "silent"}:
            raise HikPartnerError(f"Invalid panic_type: {panic_type!r}. Must be 'audible' or 'silent'.")

        panels = AlarmPanelDevice.objects.filter(site=site).prefetch_related("subsystems")
        results = []
        dispatched_panels = 0
        dispatched_partitions = 0
        failed_partitions = 0

        for panel in panels:
            if not panel.is_online:
                logger.info(
                    "trigger_global_panic: skipping offline panel %s for site %s",
                    panel.serial_number,
                    site.name,
                )
                continue
            panel_result = {"panel": panel.serial_number, "partitions": []}
            subsystems = list(panel.subsystems.all())
            if not subsystems:
                continue

            control_cap = self.get_panel_control_capabilities(panel)

            if control_cap.get("isSptOneKeyAlarmCtrl"):
                if panic_type == "silent":
                    panel_error = (
                        "silent panic is not supported by this panel via Hik-Partner Pro"
                    )
                    for subsystem in subsystems:
                        panel_result["partitions"].append({
                            "subsystem": subsystem.subsystem_number,
                            "response": {},
                            "error": panel_error,
                            "dispatched": False,
                        })
                    failed_partitions += len(subsystems)
                    results.append(panel_result)
                    continue

                request_body = {"OneKeyAlarm": {}}
                if site.longitude is not None:
                    request_body["OneKeyAlarm"]["longitude"] = round(float(site.longitude), 6)
                if site.latitude is not None:
                    request_body["OneKeyAlarm"]["latitude"] = round(float(site.latitude), 6)

                try:
                    api_response = self.client.transparent(
                        device_serial=panel.serial_number,
                        method="PUT",
                        isapi_uri="/ISAPI/SecurityCP/control/oneKeyAlarm?format=json",
                        body=request_body,
                        headers={"X-Userlevel": "0"},
                        timeout=30,
                    )
                    logger.debug(
                        "HikPartner API response for one-key alarm (serial=%s): %s",
                        panel.serial_number,
                        api_response,
                    )
                except HikPartnerError as exc:
                    panel_error = str(exc)
                    logger.error(
                        "trigger_global_panic: one-key alarm failed on panel %s: %s",
                        panel.serial_number,
                        exc,
                    )
                    for subsystem in subsystems:
                        panel_result["partitions"].append({
                            "subsystem": subsystem.subsystem_number,
                            "response": {},
                            "error": panel_error,
                            "dispatched": False,
                        })
                    failed_partitions += len(subsystems)
                    results.append(panel_result)
                    continue

                for subsystem in subsystems:
                    subsystem.status = Subsystem.STATUS_ALARM
                    subsystem.save(update_fields=["status", "updated_at"])
                    panel_result["partitions"].append({
                        "subsystem": subsystem.subsystem_number,
                        "response": api_response,
                        "error": None,
                        "dispatched": True,
                    })

                dispatched_panels += 1
                dispatched_partitions += len(subsystems)
                event = AlarmEvent.objects.create(
                    site=site,
                    event_type="Global Panic Triggered",
                    event_code="panic",
                    event_category=AlarmEvent.CATEGORY_ALARM,
                    severity=AlarmEvent.SEVERITY_CRITICAL,
                    payload={
                        "panel": panel.serial_number,
                        "panic_type": panic_type,
                        "control_mode": "one_key_alarm",
                        "partitions_triggered": len(subsystems),
                        "partitions_failed": 0,
                        "dry_run": self.client.dry_run,
                    },
                    occurred_at=timezone.now(),
                )
                from apps.alarms.tasks import dispatch_alarm_notifications
                dispatch_alarm_notifications.delay(str(event.id))
                results.append(panel_result)
                continue

            for subsystem in panel.subsystems.all():
                isapi_uri = self._map_action_to_isapi(subsystem=subsystem, action="panic")
                request_body = {"Operate": {"alarmType": panic_type}}

                # Per API guide §3.23: X-Userlevel is required for AX Pro control.
                # Use level 0 (Installer) for automated system actions.
                ax_pro_headers = {"X-Userlevel": "0"}

                api_response = {}
                partition_error = None
                if not self.client.dry_run:
                    try:
                        api_response = self.client.transparent(
                            device_serial=panel.serial_number,
                            method="PUT",
                            isapi_uri=isapi_uri,
                            body=request_body,
                            headers=ax_pro_headers,
                            timeout=30,
                        )
                        logger.debug(
                            "HikPartner API response for %s panic (serial=%s): %s",
                            panic_type, panel.serial_number, api_response
                        )
                    except HikPartnerError as exc:
                        partition_error = str(exc)
                        failed_partitions += 1
                        logger.error(
                            "trigger_global_panic: partition %s on panel %s failed: %s",
                            subsystem.subsystem_number, panel.serial_number, exc,
                        )

                partition_dispatched = partition_error is None
                if partition_dispatched:
                    subsystem.status = Subsystem.STATUS_ALARM
                    subsystem.save(update_fields=["status", "updated_at"])
                    dispatched_partitions += 1
                panel_result["partitions"].append({
                    "subsystem": subsystem.subsystem_number,
                    "response": api_response,
                    "error": partition_error,
                    "dispatched": partition_dispatched,
                })

            if panel_result["partitions"]:
                successful_partitions = sum(
                    1 for partition in panel_result["partitions"] if partition["dispatched"]
                )
                if successful_partitions:
                    dispatched_panels += 1
                    # Log a single aggregate event per panel once at least one
                    # partition accepted the panic request.
                    event = AlarmEvent.objects.create(
                        site=site,
                        event_type="Global Panic Triggered",
                        event_code="panic",
                        event_category=AlarmEvent.CATEGORY_ALARM,
                        severity=AlarmEvent.SEVERITY_CRITICAL,
                        payload={
                            "panel": panel.serial_number,
                            "panic_type": panic_type,
                            "partitions_triggered": successful_partitions,
                            "partitions_failed": len(panel_result["partitions"]) - successful_partitions,
                            "dry_run": self.client.dry_run,
                        },
                        occurred_at=timezone.now(),
                    )
                    from apps.alarms.tasks import dispatch_alarm_notifications
                    dispatch_alarm_notifications.delay(str(event.id))
                results.append(panel_result)

        return {
            "dispatched": dispatched_panels,
            "dispatched_partitions": dispatched_partitions,
            "failed_partitions": failed_partitions,
            "panels": results,
        }

    def _map_action_to_isapi(self, subsystem: Subsystem, action: str) -> str:
        partition_no = subsystem.subsystem_number
        if action == "arm":
            return f"/ISAPI/SecurityCP/control/arm/{partition_no}?ways=away&format=json"
        if action == "stay-arm":
            return f"/ISAPI/SecurityCP/control/arm/{partition_no}?ways=stay&format=json"
        if action == "disarm":
            return f"/ISAPI/SecurityCP/control/disarm/{partition_no}?format=json"
        if action == "silence":
            return f"/ISAPI/SecurityCP/control/silenceAlarm/{partition_no}?format=json"
        if action == "panic":
            return f"/ISAPI/SecurityCP/control/panicAlarm/{partition_no}?format=json"
        return f"/ISAPI/SecurityCP/control/clearAlarm/{partition_no}?format=json"

    # ------------------------------------------------------------------
    # MQ message ingestion
    # ------------------------------------------------------------------

    def _infer_control_device(self, event_desc: str, cid_event: dict = None) -> str | None:
        """
        Map a panel event description or CID metadata to a control device type.
        Robustly detects Keyfobs, Keypads and Card Readers even when the device
        type is only implied by the CID event metadata.
        """
        cid_event = cid_event or {}
        combined_text = " ".join(
            str(value or "")
            for value in (
                event_desc,
                cid_event.get("description"),
                cid_event.get("userName"),
                cid_event.get("zoneName"),
                cid_event.get("sourceName"),
                cid_event.get("deviceName"),
            )
        ).lower()

        # 1. Direct semantic match from description / actor labels
        if "key fob" in combined_text or "keyfob" in combined_text or "remote" in combined_text:
            return Zone.DEVICE_TYPE_KEYFOB
        if "keypad" in combined_text:
            return Zone.DEVICE_TYPE_KEYPAD
        if "card reader" in combined_text or ("card" in combined_text and "reader" in combined_text):
            return Zone.DEVICE_TYPE_CARD_READER

        # 2. Heuristic: arm/disarm events with device-specific identifiers usually come
        # from portable controls. userNo is a credential/user slot, not a keypad signal.
        control_text = str(cid_event.get("description") or event_desc or "").lower()
        control_patterns = (
            r"\bdisarm\b",
            r"\barm\b",
            r"\bstay\b",
            r"\baway\b",
            r"\bawayarm\b",
            r"\bstayarm\b",
            r"\bkeyfobarm\b",
            r"\bkeyfobdisarm\b",
        )
        if any(re.search(pattern, control_text) for pattern in control_patterns):
            if cid_event.get("deviceNo") not in (None, ""):
                return Zone.DEVICE_TYPE_KEYFOB

        return None

    def _infer_control_identifier(self, device_type: str, cid_event: dict | None = None) -> int:
        cid_event = cid_event or {}
        candidates = []
        if device_type == Zone.DEVICE_TYPE_KEYFOB:
            candidates = [cid_event.get("deviceNo"), cid_event.get("remoteNo"), cid_event.get("userNo")]
        elif device_type == Zone.DEVICE_TYPE_KEYPAD:
            candidates = [cid_event.get("deviceNo"), cid_event.get("keypadNo"), cid_event.get("userNo")]
        elif device_type == Zone.DEVICE_TYPE_CARD_READER:
            candidates = [cid_event.get("deviceNo"), cid_event.get("readerNo"), cid_event.get("userNo")]
        candidates.extend([cid_event.get("zone"), cid_event.get("zoneNo")])

        for value in candidates:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed >= 0:
                return parsed
        return 0

    def _ensure_control_device_presence(
        self,
        *,
        alarm_device: AlarmPanelDevice,
        subsystem: Subsystem | None,
        device_type: str,
        cid_event: dict | None,
        performed_by: str,
    ) -> None:
        cid_event = cid_event or {}
        partition_no = cid_event.get("system") or cid_event.get("partitionNo") or 1
        if subsystem is None:
            subsystem, _ = Subsystem.objects.get_or_create(
                device=alarm_device,
                subsystem_number=partition_no,
                defaults={
                    "site": alarm_device.site,
                    "name": cid_event.get("systemName") or f"Area {partition_no}",
                    "hik_subsystem_id": f"{alarm_device.serial_number}_{partition_no}",
                    "status": Subsystem.STATUS_DISARMED,
                },
            )

        control_number = self._infer_control_identifier(device_type, cid_event)
        display_name = (
            performed_by
            or cid_event.get("userName")
            or cid_event.get("zoneName")
            or f"{device_type.replace('_', ' ').title()} {control_number}".strip()
        )
        now = timezone.now()
        zone_defaults = {
            "name": display_name,
            "last_seen_at": now,
            "is_online": True,
            "network_status": "event",
            "device_number": control_number or None,
        }
        Zone.objects.update_or_create(
            subsystem=subsystem,
            zone_number=control_number,
            device_type=device_type,
            defaults=zone_defaults,
        )

        peripheral_type_map = {
            Zone.DEVICE_TYPE_KEYFOB: AlarmPeripheral.TYPE_KEYFOB,
            Zone.DEVICE_TYPE_KEYPAD: AlarmPeripheral.TYPE_KEYPAD,
            Zone.DEVICE_TYPE_CARD_READER: AlarmPeripheral.TYPE_CARD_READER,
        }
        peripheral_type = peripheral_type_map.get(device_type)
        if peripheral_type:
            AlarmPeripheral.objects.update_or_create(
                device=alarm_device,
                peripheral_type=peripheral_type,
                peripheral_number=control_number,
                defaults={
                    "site": alarm_device.site,
                    "name": display_name,
                    "serial_number": "",
                    "is_online": True,
                    "last_seen_at": now,
                    "network_status": "event",
                    "metadata": {
                        "discovered_from": "event",
                        "cid_event": {k: v for k, v in cid_event.items() if k not in {"description", "userName"}},
                    },
                },
            )

    def _ensure_module_device_presence(
        self,
        *,
        alarm_device: AlarmPanelDevice,
        cid_event: dict | None,
        performed_by: str,
    ) -> None:
        cid_event = cid_event or {}
        now = timezone.now()
        module_number = None
        for candidate in (cid_event.get("ModNo"), cid_event.get("deviceNo"), cid_event.get("zoneNo")):
            try:
                parsed = int(candidate)
            except (TypeError, ValueError):
                continue
            if parsed >= 0:
                module_number = parsed
                break
        if module_number is None:
            return

        module_name = (
            cid_event.get("deviceName")
            or cid_event.get("zoneName")
            or cid_event.get("moduleName")
            or f"Relay Module {module_number}"
        )
        metadata = {
            "discovered_from": "event",
            "event_actor": performed_by,
            "cid_event": {k: v for k, v in cid_event.items() if k not in {"description", "userName", "deviceName"}},
        }
        AlarmPeripheral.objects.update_or_create(
            device=alarm_device,
            peripheral_type=AlarmPeripheral.TYPE_OUTPUT_MODULE,
            peripheral_number=module_number,
            defaults={
                "site": alarm_device.site,
                "name": module_name,
                "serial_number": "",
                "is_online": True,
                "last_seen_at": now,
                "network_status": "event",
                "metadata": metadata,
            },
        )

        output_number = None
        for candidate in (cid_event.get("deviceNo"), cid_event.get("ModNo")):
            try:
                parsed = int(candidate)
            except (TypeError, ValueError):
                continue
            if parsed >= 0:
                output_number = parsed
                break
        if output_number is not None:
            AlarmOutput.objects.update_or_create(
                device=alarm_device,
                output_number=output_number,
                defaults={
                    "site": alarm_device.site,
                    "name": module_name,
                    "status": AlarmOutput.STATUS_OFF if hasattr(AlarmOutput, "STATUS_OFF") else "off",
                    "is_online": True,
                    "serial_number": "",
                },
            )

    def process_mq_message(self, msg: dict, *, source: str = "mq_poll") -> "AlarmEvent | None":
        """
        Normalize a single MQ message into an AlarmEvent.
        Per §3.34 response schema: formatType, accountNumber, deviceSerial, alarmData.
        alarmData commonly arrives as a JSON-encoded STRING, but the guide also
        shows JSON message examples where alarmData is already an object. Parse
        string payloads first, then extract event details and sync local state.
        """
        device_serial = msg.get("deviceSerial", "")
        raw_alarm_data = msg.get("alarmData", "")
        format_type = msg.get("formatType", "JSON")

        # alarmData is always a JSON string — parse it into a dict.
        alarm_data = raw_alarm_data
        if isinstance(raw_alarm_data, str) and raw_alarm_data.strip().startswith("{"):
            try:
                alarm_data = json.loads(raw_alarm_data)
            except (json.JSONDecodeError, ValueError):
                alarm_data = raw_alarm_data  # keep as string for XML fallback

        # Resolve the site via the device serial number
        site = None
        alarm_device = (
            AlarmPanelDevice.objects.filter(serial_number=device_serial)
            .select_related("site")
            .first()
        )
        if alarm_device:
            site = alarm_device.site

        if not site and isinstance(alarm_data, dict):
            hik_site_id = alarm_data.get("siteId")
            if hik_site_id:
                site = Site.objects.filter(hik_site_id=hik_site_id).first()

        if site is None:
            logger.warning(
                "process_mq_message: no site found for device serial %s", device_serial
            )
            return None

        # Extract event details
        # eventDescription is the human-readable action (e.g. "ArmAway", "LowBattery")
        # CIDEvent.description is its equivalent inside a cidEvent wrapper
        # event_type is the raw platform type ("cidEvent", "VMD", etc.)
        if isinstance(alarm_data, dict):
            event_type = alarm_data.get("eventType", "unknown_event")
            cid_event = alarm_data.get("CIDEvent") or {}
            # Prefer CIDEvent.description for named events, fall back to eventDescription
            event_desc = cid_event.get("description") or alarm_data.get("eventDescription", "")
            performed_by = cid_event.get("userName", "")
        else:
            m = re.search(r"<eventType>(.*?)</eventType>", str(alarm_data))
            event_type = m.group(1) if m else "unknown_event"
            cid_event = {}
            event_desc = ""
            performed_by = ""

        # Normalize the event description as suggested for robustness
        event_desc = event_desc.strip() if event_desc else ""

        event_meta = self._get_event_metadata(raw_event_type=event_type, event_desc=event_desc)
        stored_event_type = event_desc or event_meta["display_name"] or event_type
        classified_type = self._classify_event(event_desc, raw_event_type=event_type)
        event_category = event_meta["category"]
        event_severity = event_meta["severity"]
        normalized_event_type = event_meta["normalized"]

        # Deduplication: stable hash including trigger timestamp.
        # Falls back to sendTime then current time so rapid Arm->Disarm sequences
        # are never collapsed even if alarmData.triggerTime is missing.
        trigger_time = (
            alarm_data.get("triggerTime")
            or msg.get("sendTime")
            or str(timezone.now().timestamp())
        )
        raw_msg_str = f"{device_serial}:{stored_event_type}:{trigger_time}:{json.dumps(alarm_data, sort_keys=True)}"
        event_hash = hashlib.sha256(raw_msg_str.encode()).hexdigest()

        existing = AlarmEvent.objects.filter(
            site=site,
            source_event_id=event_hash
        ).first()

        if existing:
            logger.debug("Duplicate MQ skipped (Exact Hash): %s", stored_event_type)
            return existing

        # --- BROAD DEDUPLICATION (Reasoning Up) ---
        # Panel sometimes sends multiple alarmTrig for the same event with/without relationId.
        # If we have a relationId, check if it's already in the DB.
        relation_id = alarm_data.get("relationId") if isinstance(alarm_data, dict) else None
        
        # We also look for similar events from the same zone/site within 15 seconds
        zone_name = (alarm_data.get("CIDEvent") or {}).get("zoneName") if isinstance(alarm_data, dict) else None
        zone_no = (alarm_data.get("CIDEvent") or {}).get("zone") if isinstance(alarm_data, dict) else None
        
        recent_parent = AlarmEvent.objects.filter(
            site=site,
            created_at__gte=timezone.now() - timedelta(seconds=15)
        )
        
        # Prioritize matching by relationId if we have it
        if relation_id:
            match = recent_parent.filter(payload__alarmData__relationId=relation_id).order_by("-occurred_at").first()
            if match:
                if stored_event_type == match.event_type:
                    logger.debug("Duplicate MQ skipped (Relation ID match): %s", stored_event_type)
                    return match
        
        # If no relationId match, or relationId was missing, check by Zone/Sensor
        # We deduplicate sensor triggers (Alarms) broadly by Zone.
        is_sensor_trigger = event_type in ["cidEvent", "alarmTrig", "intrusion"] or \
                           event_category == AlarmEvent.CATEGORY_ALARM
        
        if is_sensor_trigger:
            # We match against any recent event that is also a sensor trigger/alarm
            match_zone = recent_parent.filter(
                models.Q(event_type=stored_event_type) | 
                models.Q(event_category=AlarmEvent.CATEGORY_ALARM) |
                models.Q(payload__alarmData__eventType__in=["alarmTrig", "cidEvent", "intrusion"])
            )
            if zone_no is not None:
                match_zone = match_zone.filter(payload__alarmData__CIDEvent__zone=zone_no)
            elif zone_name:
                match_zone = match_zone.filter(payload__alarmData__CIDEvent__zoneName=zone_name)
            else:
                match_zone = None
            
            if match_zone:
                match = match_zone.order_by("-occurred_at").first()
                if match:
                    logger.debug("Duplicate MQ skipped (Zone match): %s", stored_event_type)
                    # BACKFILL PIECE: If the new one has a relation_id but the OLD one didn't, backfill it
                    # This ensures follow-up "Linkage" can still find this parent!
                    if relation_id and not match.payload.get("alarmData", {}).get("relationId"):
                        logger.info("MQ deduplication: Backfilling relationId %s to event %s", relation_id, match.id)
                        if "alarmData" not in match.payload: match.payload["alarmData"] = {}
                        match.payload["alarmData"]["relationId"] = relation_id
                        match.save(update_fields=["payload"])
                    return match

        occurred_at = self._extract_event_occurred_at(alarm_data, msg)

        logger.info("MQ event: %s (device=%s)", stored_event_type, device_serial)

        # Sync model state from the event description (the source of truth).
        # The timestamp guard prevents delayed/backlogged deliveries from rolling
        # a partition or zone back to an older state.
        subsystem = zone = None
        if event_desc and alarm_device:
            subsystem, zone = self._sync_state_from_event(
                alarm_device,
                cid_event,
                event_desc,
                alarm_data,
                occurred_at=occurred_at,
            )

        if alarm_device:
            panel_fields_to_update = set()
            if normalized_event_type == "ac_power_lost":
                alarm_device.battery_status = AlarmPanelDevice.BATTERY_LOW
                panel_fields_to_update.add("battery_status")
            elif normalized_event_type == "ac_power_restored":
                alarm_device.battery_status = AlarmPanelDevice.BATTERY_OK
                panel_fields_to_update.add("battery_status")
            if panel_fields_to_update:
                panel_fields_to_update.update({"updated_at"})
                alarm_device.save(update_fields=list(panel_fields_to_update))

        # Extract picture references for Linkage events (PIR cameras with built-in cam).
        # Per §A.3.6: alarmData.pictureList is an array of {id, url} where url is either:
        #   - https://... (direct download, type 2 URL)
        #   - ISAPI_FILES/... (requires /v1/alarm/pictureurl call to get a real URL)
        pictures = []
        needs_image_fetch = False
        if isinstance(alarm_data, dict):
            for pic in alarm_data.get("pictureList", []):
                url = pic.get("url", "")
                if url:
                    is_internal = url.startswith("ISAPI_FILES")
                    if is_internal:
                        needs_image_fetch = True
                    media_id = pic.get("id", "")
                    media_type = resolve_picture_media_type(
                        url=url,
                        media_id=media_id,
                        stored_type=pic.get("type", ""),
                        alarm_data=alarm_data,
                        probe_remote=False,
                    )
                    pictures.append({
                        "id": media_id,
                        "url": url,
                        "needs_url_fetch": is_internal,
                        "type": media_type,
                    })

        # --- IMPROVED LINKAGE HANDLER (Reasoning Up) ---
        # Hikvision "Linkage" events follow an alarm to provide video verification.
        # Check event_type directly as AX Pro sometimes sends empty descriptions for Linkage.
        if event_type == "Linkage" and isinstance(alarm_data, dict):
            relation_id = alarm_data.get("relationId")
            if relation_id:
                parent = AlarmEvent.objects.filter(
                    site=site,
                    payload__alarmData__relationId=relation_id
                ).exclude(event_type="Linkage").order_by("-occurred_at").first()

                if parent:
                    logger.info("MQ Linkage: Merging media into parent event %s (relationId=%s)", parent.id, relation_id)
                    existing_media = parent.payload.get("pictures", [])
                    
                    # Deduplicate by media ID/URL
                    new_count = 0
                    existing_urls = {p.get("url") for p in existing_media}
                    for p in pictures:
                        if p.get("url") not in existing_urls:
                            existing_media.append(p)
                            new_count += 1
                                    
                    if new_count > 0:
                        parent.payload["pictures"] = existing_media
                        parent.save(update_fields=["payload"])
                        
                        # If the new media needs URL exchange, trigger it for the parent
                        if needs_image_fetch:
                            from apps.alarms.tasks import fetch_alarm_image_url
                            fetch_alarm_image_url.delay(str(parent.id))
                    
                    # Successfully handled as a merge. Return parent instead of creating new Linkage row.
                    return parent

        event = AlarmEvent.objects.create(
            site=site,
            subsystem=subsystem,
            zone=zone,
            event_type=stored_event_type,
            event_code=event_type,
            performed_by=performed_by,
            event_category=event_category,
            severity=event_severity,
            source_event_id=event_hash,
            payload={
                "formatType": format_type,
                "deviceSerial": device_serial,
                "alarmData": alarm_data,
                "pictures": pictures,
                "source": source,
                "event_name": event_meta["display_name"],
                "normalized_event_type": normalized_event_type,
                "raw_event_type": event_type,
            },
            occurred_at=occurred_at,
        )

        # Trigger notification dispatch for ALL MQ-ingested events.
        # The dispatch task itself will manage final filtering based on site settings.
        from apps.alarms.tasks import dispatch_alarm_notifications
        dispatch_alarm_notifications.delay(str(event.id))

        # If there are internal picture paths, trigger a background task to exchange
        # them for public viewable URLs immediately.
        if needs_image_fetch:
            from apps.alarms.tasks import fetch_alarm_image_url
            fetch_alarm_image_url.delay(str(event.id))

        # ── Fallback Discovery ──
        # If this event came from a control device (keyfob, keypad, card), ensure it 
        # exists in our database and update its 'last_seen_at' timestamp.
        module_event_desc = str(cid_event.get("description") or event_desc or "").lower()
        if "exmodule" in module_event_desc and alarm_device:
            self._ensure_module_device_presence(
                alarm_device=alarm_device,
                cid_event=cid_event,
                performed_by=performed_by,
            )

        device_type = self._infer_control_device(event_desc, cid_event)
        if device_type and alarm_device:
            self._ensure_control_device_presence(
                alarm_device=alarm_device,
                subsystem=subsystem,
                device_type=device_type,
                cid_event=cid_event,
                performed_by=performed_by,
            )

        return event

    # Event detection keywords (Reasoning Up)
    _KW_ALARM = {"alarm", "panic", "intrusion", "fire", "emergency", "medical", "gas", "leak", "breach", "trouble", "distress"}
    _KW_ARM = {"arm away", "armed away", "away arm", "awayarm", "force arm", "auto arm", "armaway", "onekeyarm", "keyfobarm", "armaway", "away", "armed"}
    _KW_STAY = {"stay arm", "stay arming", "stayarm", "home arm", "stayarmoperation", "stay", "partial arm"}
    _KW_DISARM = {"disarm", "disarming", "disarmed", "keyfobdisarm", "disarmoperation"}
    _KW_BYPASS = {"bypasszone", "zone bypass", "bypass"}
    _KW_UNBYPASS = {"bypassrecover", "unbypass", "bypass restore", "bypass recover", "bypass clear"}
    _KW_BAT_OK = {"battery restore", "battery recovered", "battery ok", "low battery restore"}
    _KW_TAMPER_CLEAR = {"tamper restore", "tamper recovered", "tamper clear"}
    
    # eventDescription → Zone state / health keywords
    _KW_RESTORE = {"restore", "recovery", "normal", "recovered", "cleared", "closed"}
    _KW_OPEN = {"door open", "dooropen", "open", "opened"}
    _KW_LOW_BAT = {"low battery", "lowbattery"}
    _KW_TAMPER = {"tamper", "tamper alarm", "tamperalarm"}
    _KW_ONLINE = {"online", "connected"}
    _KW_OFFLINE = {"offline", "disconnected"}
    
    _KW_INFO = {"snapshot", "heartbeat", "keepalive"}

    def _get_event_metadata(self, raw_event_type: str, event_desc: str) -> dict:
        raw_key = str(raw_event_type or "").strip().lower()
        desc_key = str(event_desc or "").strip().lower()
        compact_desc = self._normalize_event_lookup_key(desc_key)

        if raw_key in self.EVENT_META_BY_RAW_TYPE:
            return self.EVENT_META_BY_RAW_TYPE[raw_key]

        for candidate in (desc_key, compact_desc):
            if not candidate:
                continue
            for known_key, metadata in self.EVENT_META_BY_DESC.items():
                if self._normalize_event_lookup_key(known_key) == candidate:
                    normalized, display_name, category, severity = metadata
                    return {
                        "normalized": normalized,
                        "display_name": display_name,
                        "category": category,
                        "severity": severity,
                    }

        if desc_key in self.EVENT_META_BY_RAW_TYPE:
            return self.EVENT_META_BY_RAW_TYPE[desc_key]

        display_name = humanize_event_label(event_desc or raw_event_type)
        return {
            "normalized": "unknown",
            "display_name": display_name,
            "category": AlarmEvent.CATEGORY_INFO,
            "severity": AlarmEvent.SEVERITY_LOW,
        }

    def _classify_event(self, event_desc: str, raw_event_type: str = "") -> str:
        metadata = self._get_event_metadata(raw_event_type=raw_event_type, event_desc=event_desc)
        normalized = metadata.get("normalized", "")
        if normalized in self.NORMALIZED_EVENT_CLASS:
            return self.NORMALIZED_EVENT_CLASS[normalized]

        if not event_desc:
            return "UNKNOWN"
            
        desc = event_desc.lower().strip()
        
        # Priority 1: ALARM (Critical)
        if any(kw in desc for kw in self._KW_ALARM):
            return "ALARM"
            
        # Priority 2: DISARM -> STAY -> ARM
        if any(kw in desc for kw in self._KW_DISARM):
            return "DISARM"
        if any(kw in desc for kw in self._KW_STAY):
            return "STAY"
        if any(kw in desc for kw in self._KW_ARM):
            return "ARM"

        if any(kw in desc for kw in self._KW_UNBYPASS):
            return "UNBYPASS"
        if any(kw in desc for kw in self._KW_BYPASS):
            return "BYPASS"
        if any(kw in desc for kw in self._KW_TAMPER_CLEAR):
            return "TAMPER_CLEAR"
        if any(kw in desc for kw in self._KW_BAT_OK):
            return "BATTERY_OK"
            
        # Priority 3: State Changes
        if any(kw in desc for kw in self._KW_RESTORE):
            return "RESTORE"
        if any(kw in desc for kw in self._KW_OPEN):
            return "OPEN"
        if any(kw in desc for kw in self._KW_TAMPER):
            return "TAMPER"
        if any(kw in desc for kw in self._KW_LOW_BAT):
            return "LOW_BATTERY"
            
        # Priority 4: Health
        if any(kw in desc for kw in self._KW_ONLINE):
            return "ONLINE"
        if any(kw in desc for kw in self._KW_OFFLINE):
            return "OFFLINE"
            
        # Priority 5: Info
        if any(kw in desc for kw in self._KW_INFO):
            return "INFO"
            
        return "UNKNOWN"

    def _extract_event_occurred_at(self, alarm_data, msg: dict) -> datetime:
        candidates = []
        if isinstance(alarm_data, dict):
            candidates.extend(
                [
                    alarm_data.get("triggerTime"),
                    alarm_data.get("eventTime"),
                    alarm_data.get("timestamp"),
                ]
            )
        candidates.append(msg.get("sendTime"))

        for raw_value in candidates:
            parsed = self._parse_hik_datetime(raw_value)
            if parsed is not None:
                return parsed

        return timezone.now()

    @staticmethod
    def _parse_hik_datetime(raw_value) -> datetime | None:
        if raw_value in (None, ""):
            return None

        if isinstance(raw_value, (int, float)):
            raw_str = str(int(raw_value))
        else:
            raw_str = str(raw_value).strip()

        if not raw_str:
            return None

        dt = parse_datetime(raw_str)
        if dt is not None:
            if timezone.is_naive(dt):
                return timezone.make_aware(dt, dt_timezone.utc)
            return dt.astimezone(dt_timezone.utc)

        if raw_str.isdigit() and len(raw_str) >= 10:
            timestamp_value = int(raw_str)
            if len(raw_str) >= 13:
                timestamp_value = timestamp_value / 1000
            try:
                return datetime.fromtimestamp(timestamp_value, tz=dt_timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None

        return None

    def _sync_state_from_event(
        self,
        panel: "AlarmPanelDevice",
        cid_event: dict,
        event_desc: str,
        alarm_data: dict = None,
        occurred_at: datetime | None = None,
    ) -> tuple["Subsystem | None", "Zone | None"]:
        """
        Update Subsystem and Zone models from an eventDescription string using
        the centralised _classify_event dispatcher.
        cid_event provides the partition number (system) and optional zone number.
        Returns (subsystem, zone) objects if matched.
        """
        site = panel.site
        partition_no = cid_event.get("system", 1)
        
        # Resolve zone number from CID event or raw alarm data (common for Linkage events)
        zone_no = cid_event.get("zone") or cid_event.get("zoneNo")
        if zone_no is None and alarm_data:
            zone_no = alarm_data.get("deviceNo") or alarm_data.get("zoneNo")

        subsystem = Subsystem.objects.filter(
            site=site, subsystem_number=partition_no
        ).first()

        zone = None
        if zone_no is not None and subsystem:
            zone = Zone.objects.filter(
                subsystem=subsystem,
                zone_number=zone_no
            ).first()

        event_type = self._classify_event(event_desc)

        state_event_types = {"ARM", "STAY", "DISARM", "ALARM"}
        stale_for_subsystem = False
        if subsystem and occurred_at and event_type in state_event_types:
            stale_for_subsystem = AlarmEvent.objects.filter(
                site=site,
                subsystem=subsystem,
                occurred_at__gt=occurred_at,
                event_category__in=[
                    AlarmEvent.CATEGORY_ARM,
                    AlarmEvent.CATEGORY_ALARM,
                    AlarmEvent.CATEGORY_SYSTEM,
                ],
            ).exists()

        stale_for_zone = False
        if zone and occurred_at:
            stale_for_zone = AlarmEvent.objects.filter(
                site=site,
                zone=zone,
                occurred_at__gt=occurred_at,
            ).exclude(event_category=AlarmEvent.CATEGORY_INFO).exists()

        # ── Subsystem state ───────────────────────────────────────────────
        if subsystem and not stale_for_subsystem:
            if event_type == "ARM":
                subsystem.status = Subsystem.STATUS_ARMED

            elif event_type == "STAY":
                subsystem.status = Subsystem.STATUS_STAY

            elif event_type == "DISARM":
                subsystem.status = Subsystem.STATUS_DISARMED
                Zone.objects.filter(subsystem=subsystem, state=Zone.STATE_ALARM).update(
                    state=Zone.STATE_NORMAL
                )

            elif event_type == "ALARM":
                subsystem.status = Subsystem.STATUS_ALARM

            subsystem.save(update_fields=["status", "updated_at"])
        elif subsystem and stale_for_subsystem:
            logger.info(
                "_sync_state_from_event: skipped stale %s for subsystem %s "
                "(event time %s)",
                event_type,
                subsystem.id,
                occurred_at,
            )

        # ── Zone state ────────────────────────────────────────────────────
        if zone and not stale_for_zone:
            is_disarmed = subsystem and subsystem.status == Subsystem.STATUS_DISARMED
            zone_modified = False

            if event_type == "ALARM":
                zone.state = Zone.STATE_OPEN if is_disarmed else Zone.STATE_ALARM
                zone_modified = True

            elif event_type == "OPEN":
                zone.state = Zone.STATE_OPEN
                zone_modified = True

            elif event_type == "RESTORE":
                zone.state = Zone.STATE_NORMAL
                zone_modified = True

            elif event_type == "BYPASS":
                zone.state = Zone.STATE_BYPASSED
                zone_modified = True

            elif event_type == "UNBYPASS":
                zone.state = Zone.STATE_NORMAL
                zone_modified = True

            elif event_type == "LOW_BATTERY":
                zone.low_battery = True
                zone_modified = True

            elif event_type == "BATTERY_OK":
                zone.low_battery = False
                zone_modified = True

            elif event_type == "TAMPER":
                zone.tamper = True
                zone_modified = True

            elif event_type == "TAMPER_CLEAR":
                zone.tamper = False
                zone_modified = True

            if zone_modified:
                zone.save()
        elif zone and stale_for_zone:
            logger.info(
                "_sync_state_from_event: skipped stale %s for zone %s "
                "(event time %s)",
                event_type,
                zone.id,
                occurred_at,
            )

        # ── Panel connectivity ────────────────────────────────────────────
        if event_type == "ONLINE":
            panel.is_online = True
            panel.last_seen_at = timezone.now()
            panel.save(update_fields=["is_online", "last_seen_at", "updated_at"])

        elif event_type == "OFFLINE":
            panel.is_online = False
            panel.save(update_fields=["is_online", "updated_at"])

        elif event_type == "UNKNOWN":
            logger.debug(
                "_sync_state_from_event: unhandled eventDescription=%r for panel %s",
                event_desc, panel.serial_number,
            )

        return subsystem, zone

    # ------------------------------------------------------------------
    # Webhook configuration (admin operations)
    # ------------------------------------------------------------------

    def query_webhook_config(self) -> dict:
        """Per §3.67."""
        return self.client.get_webhook_config()

    def save_webhook_config(
        self,
        callback_url: str,
        retry_times: int = 3,
        retry_delay_ms: int = 1000,
        sign_secret: str = None,
    ) -> dict:
        """
        Per §3.68. callback_url must be HTTPS.

        Omit signSecret unless a dedicated webhook secret is configured. Hik
        defaults it to the app SecretKey, and the explicit field has stricter
        8-32 alphanumeric validation than some generated API secrets.
        """
        configured_sign_secret = sign_secret
        if configured_sign_secret is None:
            configured_sign_secret = settings.HIK_PARTNER.get("WEBHOOK_SIGN_SECRET") or None

        return self.client.save_webhook_config(
            callback_url=callback_url,
            retry_times=retry_times,
            retry_delay_ms=retry_delay_ms,
            sign_secret=configured_sign_secret,
        )

    def delete_webhook_config(self) -> dict:
        """Per §3.69."""
        return self.client.delete_webhook_config()

    # ------------------------------------------------------------------
    # Alarm picture URL — §3.36
    # ------------------------------------------------------------------

    def get_alarm_picture_url(self, file_path: str) -> dict:
        """
        Fetch a 2-hour download URL for an alarm image.
        file_path comes from alarmData in an MQ message (starts with ISAPI_FILES/).
        Returns {"pictureUrl": "...", "encrypt": bool}.
        """
        return self.client.get_alarm_picture_url(file_path)

    # ------------------------------------------------------------------
    # Site provisioning on Hik platform — §3.3, §3.6
    # ------------------------------------------------------------------

    def provision_hik_site(
        self,
        name: str,
        time_zone: int = 222,
        **kwargs,
    ) -> str:
        """
        Create a site on the Hik-Partner Pro platform and return its Hik-assigned ID.
        Because /site/add returns no ID, we search by name immediately after creation.
        Raises HikPartnerError if the site cannot be located after creation.
        In dry-run mode returns a placeholder ID so local provisioning still works.
        """
        if self.client.dry_run:
            return "dry-run-site-id"

        self.client.create_site(name=name, time_zone=time_zone, **kwargs)

        # /site/add gives no ID — search by exact name to retrieve it
        resp = self.client.search_sites(search=name, page=1, page_size=50)
        rows = resp.get("data", {}).get("rows", [])
        for row in rows:
            if row.get("siteName", "").strip() == name.strip():
                return row["id"]

        # Fallback: take the first result if exact match not found (e.g. trimmed whitespace)
        if rows:
            logger.warning(
                "provision_hik_site: exact name match not found for '%s'; using first result '%s'",
                name,
                rows[0].get("siteName"),
            )
            return rows[0]["id"]

        raise HikPartnerError(
            f"Site '{name}' was created on Hik platform but could not be located via search."
        )

    # ------------------------------------------------------------------
    # Device management — §3.18, §3.19
    # ------------------------------------------------------------------

    def add_devices_to_hik_site(self, site: Site, device_list: list) -> dict:
        """
        Register one or more devices against a site on the Hik platform,
        then sync local models so the new devices appear immediately.
        device_list: [{"deviceSerial": "...", "validateCode": "...", "extendInfo": "..."}, ...]
        Returns the Hik API response with addSuccessList / addFailedList.
        """
        result = self.client.add_devices(
            site_id=site.hik_site_id,
            device_list=device_list,
        )
        # Pull the new devices into local DB regardless of partial failures
        try:
            self.sync_site_devices(site)
        except Exception as exc:
            logger.warning("add_devices_to_hik_site: post-add sync failed: %s", exc)

        return result.get("data", result)

    def remove_device_from_hik(self, device_id: str) -> None:
        """
        Delete a device from the Hik platform and remove matching local records.
        device_id is the Hik-side ID stored as hik_device_id on AlarmPanelDevice.

        LAP006009 ("device does not exist or no permission") is treated as a non-error:
        the device was never on the Hik platform (e.g. manually registered locally), so
        we skip the platform call and just delete the local records.
        """
        if not self.client.dry_run:
            try:
                self.client.delete_device(device_id)
            except HikPartnerError as exc:
                if exc.error_code == "LAP006009":
                    logger.info(
                        "remove_device_from_hik: device %s not found on Hik platform "
                        "(LAP006009) — removing local records only.",
                        device_id,
                    )
                else:
                    raise

        # Clean up local records
        AlarmPanelDevice.objects.filter(hik_device_id=device_id).delete()

    # ------------------------------------------------------------------
    # Installer search — §3.2
    # ------------------------------------------------------------------

    def search_installers(
        self, search: str = "", page: int = 1, page_size: int = 20
    ) -> dict:
        """Search employees/installers on the Hik platform. Returns raw data dict."""
        return self.client.search_installers(search=search, page=page, page_size=page_size).get(
            "data", {}
        )

    # ------------------------------------------------------------------
    # ARC service — §3.37–3.39
    # ------------------------------------------------------------------

    def list_arc_devices(
        self,
        page: int = 1,
        page_size: int = 20,
        site_id: str = None,
        device_serials: list = None,
    ) -> dict:
        return self.client.list_arc_devices(
            page=page, page_size=page_size, site_id=site_id, device_serials=device_serials
        ).get("data", {})

    def enable_arc_for_device(self, device_serial: str, arc_id: str) -> dict:
        """Enable ARC monitoring for a device. Returns permission status."""
        resp = self.client.enable_arc(device_serial=device_serial, arc_id=arc_id)
        return resp.get("data", resp)

    def disable_arc_for_device(self, device_serial: str) -> None:
        self.client.disable_arc(device_serial=device_serial)

    def refresh_site_health(self, site: Site) -> dict:
        """
        Update panel online status and zone health for a site.

        Primary path: POST /api/hpcgw/v1/site/health/report — returns battery, tamper,
        signal, work status per device and zone.

        Fallback (LAP008128 / permission denied): uses:
          - POST /api/hpcgw/v1/device/list for panel online status
          - Transparent ISAPI /ISAPI/SecurityCP/diagnostic/zones for per-zone health
        """
        if not site.hik_site_id:
            return {"skipped": True, "reason": "no hik_site_id"}

        # ── Try the full health report API first ──────────────────────────
        if not self.client.dry_run:
            try:
                resp = self.client.get_site_health_report(site.hik_site_id)
            except HikPartnerError as exc:
                if exc.error_code and exc.error_code.startswith("LAP008"):
                    logger.warning(
                        "refresh_site_health: skipping site %s due to LAP008xxx exception (invalid or revoked)", 
                        site.name
                    )
                    return {"skipped": True, "reason": "api error (invalid site permission)"}
                raise
            data = resp.get("data") or {}
            report_detail = data.get("reportDetail") or []
            if isinstance(report_detail, list) and report_detail:
                return self._apply_health_report(site, report_detail)
            logger.info(
                "refresh_site_health: health report empty for site %s — falling back",
                site.name,
            )

        # ── Fallback: device list for online status + ISAPI for zone health ──
        return self._refresh_health_via_isapi(site)

    def _apply_health_report(self, site: Site, report_detail: list) -> dict:
        """Apply a parsed health report list to local DB records."""
        panels_updated = zones_updated = outputs_updated = peripherals_updated = 0
        now = timezone.now()

        for device_report in report_detail:
            device_serial = device_report.get("deviceSerial", "")
            online = device_report.get("onlineStatus", 0) == 1
            alarm_status = device_report.get("alarmDeviceStatus") or {}

            panel = AlarmPanelDevice.objects.filter(serial_number=device_serial).first()
            if panel:
                panel.is_online = online
                panel.battery_status = self._resolve_panel_power_status(
                    panel=panel,
                    alarm_status=alarm_status,
                )
                panel.work_status = alarm_status.get("workStatus", "unknown")
                panel.cloud_status = alarm_status.get("cloudStatus", "unknown")
                panel.last_health_check = now
                if online:
                    panel.last_seen_at = now
                panel.save(update_fields=[
                    "is_online", "battery_status", "work_status",
                    "cloud_status", "last_health_check", "last_seen_at", "updated_at",
                ])
                panels_updated += 1

            for zone_report in alarm_status.get("zones", []):
                zone_id = zone_report.get("zoneId")
                if zone_id is None:
                    continue
                low_batt = zone_report.get("batteryStatus", "ok").lower() == "low"
                is_tamper = str(zone_report.get("tamperStatus", "false")).lower() == "true"
                signal = self._normalize_signal_strength(zone_report.get("signalStrength"))
                bypass = str(zone_report.get("byPassStatus", "No")).lower() == "yes"
                is_online = zone_report.get("networkStatus", "").lower() not in {"offline", "disconnected"}

                qs = Zone.objects.filter(
                    subsystem__device__serial_number=device_serial,
                    zone_number=zone_id,  # health report zoneId and DB zone_number are both 0-indexed
                )
                updates = {
                    "low_battery": low_batt,
                    "tamper": is_tamper,
                    "signal_strength": signal,
                    "network_status": zone_report.get("networkStatus", ""),
                    "diagnostics_result": zone_report.get("diagnosticsResult", ""),
                    "external_power": zone_report.get("externalPower", ""),
                    "is_online": is_online,
                    "last_seen_at": now,
                }
                if bypass:
                    updates["state"] = Zone.STATE_BYPASSED
                zones_updated += qs.update(**updates)

            if panel:
                peripherals_updated += self._sync_peripheral_inventory(site=site, panel=panel, alarm_status=alarm_status, now=now)
                outputs_updated += self._sync_outputs_via_isapi(panel)

        return {
            "panels_updated": panels_updated,
            "zones_updated": zones_updated,
            "peripherals_updated": peripherals_updated,
            "outputs_updated": outputs_updated,
        }

    def _refresh_health_via_isapi(self, site: Site) -> dict:
        """
        Fallback health refresh using:
        - /api/hpcgw/v1/device/list to update panel is_online
        - /ISAPI/SecurityCP/diagnostic/zones for zone battery/tamper/signal
        """
        panels_updated = zones_updated = outputs_updated = 0
        now = timezone.now()

        # Step 1: update online status from device list
        try:
            for dev_info in self._fetch_site_device_list(site.hik_site_id):
                serial = dev_info.get("deviceSerial", "")
                online = dev_info.get("deviceOnlineStatus") == 1
                updated = AlarmPanelDevice.objects.filter(
                    serial_number=serial, site=site
                ).update(is_online=online, last_health_check=now)
                if online and updated:
                    AlarmPanelDevice.objects.filter(
                        serial_number=serial, site=site
                    ).update(last_seen_at=now)
                panels_updated += updated
        except Exception as exc:
            logger.warning("_refresh_health_via_isapi: device list failed for %s: %s", site.name, exc)

        # Step 2: zone health via transparent ISAPI
        # Try diagnostic endpoint first (newer firmware), fall back to status endpoint.
        for panel in AlarmPanelDevice.objects.filter(site=site, is_online=True):
            zone_entries = []

            for isapi_uri in (
                "/ISAPI/SecurityCP/diagnostic/zones?format=json",
                "/ISAPI/SecurityCP/status/zones?format=json",
            ):
                try:
                    resp = self.client.transparent(
                        device_serial=panel.serial_number,
                        method="GET",
                        isapi_uri=isapi_uri,
                        timeout=self._status_timeout(),
                    )
                    zone_entries = resp.get("ZoneList", [])
                    if zone_entries:
                        logger.info(
                            "_refresh_health_via_isapi: got %d zones from %s for panel %s",
                            len(zone_entries), isapi_uri, panel.serial_number,
                        )
                        break
                except Exception as exc:
                    logger.warning(
                        "_refresh_health_via_isapi: %s failed for panel %s: %s",
                        isapi_uri, panel.serial_number, exc,
                    )

            for entry in zone_entries:
                zone_data = entry.get("Zone", {})
                zone_no = zone_data.get("id")  # 0-indexed sequential id, matches DB zone_number
                if zone_no is None:
                    continue
                if zone_data.get("status") == "notRelated":
                    continue
                signal = self._normalize_signal_strength(zone_data.get("signal"))
                charge_value = zone_data.get("chargeValue")
                device_no = zone_data.get("deviceNo")
                state = Zone.STATE_NORMAL
                if zone_data.get("alarm"):
                    state = Zone.STATE_ALARM
                elif zone_data.get("bypassed"):
                    state = Zone.STATE_BYPASSED
                elif zone_data.get("status") == "trigger":
                    state = Zone.STATE_ALARM
                elif zone_data.get("magnetOpenStatus") is True:
                    state = Zone.STATE_OPEN

                qs = Zone.objects.filter(subsystem__device=panel, zone_number=zone_no, device_type=Zone.DEVICE_TYPE_ZONE)
                if qs.exists():
                    updates = self._base_zone_defaults(
                        zone_data,
                        state=state,
                        is_online=zone_data.get("status") != "offline",
                        magnet_open=zone_data.get("magnetOpenStatus"),
                    )
                    updates["signal_strength"] = signal
                    if charge_value is not None:
                        updates["charge_value"] = charge_value
                    if device_no is not None:
                        updates["device_number"] = device_no
                    updates["last_seen_at"] = now
                    qs.update(**updates)
                    zones_updated += qs.count()

            outputs_updated += self._sync_outputs_via_isapi(panel)

        return {
            "panels_updated": panels_updated,
            "zones_updated": zones_updated,
            "outputs_updated": outputs_updated,
            "via_fallback": True,
        }

    def bypass_zone(self, subsystem: "Subsystem", zone_no: int) -> dict:
        """
        Bypass a single zone on the panel via transparent ISAPI.
        Per §A.4: PUT /ISAPI/SecurityCP/control/bypass/{zoneNo}?format=json
        """
        return self.client.transparent(
            device_serial=subsystem.device.serial_number,
            method="PUT",
            isapi_uri=f"/ISAPI/SecurityCP/control/bypass/{zone_no}?format=json",
            headers={"X-Userlevel": "1"},
        )

    def _event_type_for_action(self, action: str) -> str:
        return {
            "arm": "arm_success",
            "disarm": "disarm_success",
            "stay-arm": "stay_arm_success",
            "clear-alarm": "alarm_cleared",
            "silence": "silence_success",
            "panic": "panic_alarm_triggered",
        }[action]
