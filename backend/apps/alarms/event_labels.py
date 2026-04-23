from __future__ import annotations

import re


_LOOKUP_NORMALIZER = re.compile(r"[\s_\-()&]+")
_CAMEL_BOUNDARY_1 = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_CAMEL_BOUNDARY_2 = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")

_FRIENDLY_EVENT_LABELS = {
    "acdown": "AC Power Lost",
    "acrecov": "AC Power Restored",
    "addexmodule": "Module Added",
    "alarmtrig": "Alarm Triggered",
    "armaway": "Arm Away",
    "armsuccess": "Arm Successful",
    "awayarm": "Arm Away",
    "clearalarm": "Alarm Cleared",
    "delexmodule": "Module Removed",
    "disarmoperation": "Disarm",
    "disarmsuccess": "Disarm Successful",
    "manualrep": "Manual Capture",
    "mobilezoneinstantalarm": "Instant Zone Alarm",
    "offline": "Offline",
    "online": "Online",
    "panicalarm": "Panic Alarm",
    "panelstatuscommunications": "Panel Communication Status",
    "panelstatuspowerbattery": "Panel Power Status",
    "peripheralsstatus": "Peripherals Status",
    "snapshot": "Snapshot Captured",
    "softzonepanicalarm": "Panic Alarm",
    "stayarm": "Stay Arm",
    "stayarmoperation": "Stay Arm",
    "stayarmsuccess": "Stay Arm Successful",
    "systemoperation": "System Operation",
    "wirednetworkfault": "Wired Network Fault",
    "wirednetworkfaultrecover": "Wired Network Fault Restored",
    "zonestatus": "Zone Status",
}

_TOKEN_LABELS = {
    "ac": "AC",
    "cid": "CID",
    "io": "I/O",
    "ip": "IP",
    "pir": "PIR",
    "sms": "SMS",
    "vmd": "VMD",
}


def normalize_event_label_lookup(value: str) -> str:
    return _LOOKUP_NORMALIZER.sub("", str(value or "").strip().lower())


def humanize_event_label(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        return "Unknown Event"

    normalized = normalize_event_label_lookup(value)
    if normalized in _FRIENDLY_EVENT_LABELS:
        return _FRIENDLY_EVENT_LABELS[normalized]

    spaced = value.replace("_", " ").replace("-", " ")
    spaced = _CAMEL_BOUNDARY_1.sub(" ", spaced)
    spaced = _CAMEL_BOUNDARY_2.sub(" ", spaced)
    parts = [part for part in spaced.split() if part]
    if not parts:
        return "Unknown Event"

    return " ".join(_TOKEN_LABELS.get(part.lower(), part.title()) for part in parts)
