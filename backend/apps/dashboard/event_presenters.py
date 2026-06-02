from __future__ import annotations

from apps.alarms.event_labels import humanize_event_label
from apps.alarms.media import collect_related_event_media
from apps.alarms.models import AlarmEvent
from django.utils import timezone


CATEGORY_LABELS = {
    AlarmEvent.CATEGORY_ALARM: "Alarm",
    AlarmEvent.CATEGORY_ARM: "Arm / Disarm",
    AlarmEvent.CATEGORY_SYSTEM: "System",
    AlarmEvent.CATEGORY_HEALTH: "Health",
    AlarmEvent.CATEGORY_INFO: "Info",
}

SEVERITY_LABELS = {
    AlarmEvent.SEVERITY_CRITICAL: "Critical",
    AlarmEvent.SEVERITY_HIGH: "High",
    AlarmEvent.SEVERITY_MEDIUM: "Medium",
    AlarmEvent.SEVERITY_LOW: "Low",
}


def _humanize_event_value(raw_value: str) -> str:
    return humanize_event_label(raw_value)


def _has_event_media(event: AlarmEvent) -> tuple[bool, int]:
    media_items = collect_related_event_media(event)
    if media_items:
        return True, len(media_items)
    return False, 0


def should_hide_console_event(event: AlarmEvent) -> bool:
    payload = event.payload or {}
    normalized_type = str(payload.get("normalized_event_type") or "").strip()
    if normalized_type != "snapshot_captured":
        return False

    alarm_data = payload.get("alarmData") or {}
    relation_id = alarm_data.get("relationId") if isinstance(alarm_data, dict) else None
    if not relation_id:
        return False

    return AlarmEvent.objects.filter(site=event.site, payload__alarmData__relationId=relation_id).exclude(
        id=event.id
    ).exists()


def _event_location_label(event: AlarmEvent) -> str:
    if event.zone_id and event.zone:
        return event.zone.name
    if event.subsystem_id and event.subsystem:
        return event.subsystem.name
    return "Site-wide"


def _event_operator_label(event: AlarmEvent, payload: dict) -> str:
    return (
        payload.get("operator_name")
        or payload.get("operatorName")
        or payload.get("user_name")
        or payload.get("userName")
        or event.performed_by
        or "System"
    )


def _event_summary(event: AlarmEvent, *, display_name: str, location_label: str, operator_label: str) -> str:
    category = event.event_category or AlarmEvent.CATEGORY_INFO
    has_specific_location = location_label != "Site-wide"
    has_operator = operator_label != "System"

    if category == AlarmEvent.CATEGORY_ALARM:
        if has_specific_location and has_operator:
            return f"{location_label} alarm activity was recorded by {operator_label}."
        if has_specific_location:
            return f"{location_label} alarm activity was recorded."
        return "Alarm activity was recorded on this site."

    if category == AlarmEvent.CATEGORY_ARM:
        if has_specific_location and has_operator:
            return f"{location_label} state was updated by {operator_label}."
        if has_specific_location:
            return f"{location_label} arm state changed."
        if has_operator:
            return f"Site state was updated by {operator_label}."
        return "Site arm state changed."

    if category == AlarmEvent.CATEGORY_HEALTH:
        if has_specific_location:
            return f"{location_label} reported a health update."
        return "System health status was updated."

    if category == AlarmEvent.CATEGORY_SYSTEM:
        if has_operator:
            return f"{display_name} was recorded by {operator_label}."
        return f"{display_name} was recorded for this site."

    if has_operator:
        return f"{display_name} was recorded by {operator_label}."
    return f"{display_name} was recorded."


def serialize_console_event(event: AlarmEvent) -> dict:
    payload = event.payload or {}
    normalized_type = str(payload.get("normalized_event_type") or "").strip()
    type_source = event.event_type if normalized_type in {"", "unknown"} else normalized_type
    type_label = _humanize_event_value(type_source)
    display_name = humanize_event_label(str(payload.get("event_name") or type_label).strip() or type_label)
    category = event.event_category or AlarmEvent.CATEGORY_INFO
    severity = event.severity or AlarmEvent.SEVERITY_LOW
    location_label = _event_location_label(event)
    operator_label = _event_operator_label(event, payload)
    has_pictures, media_count = _has_event_media(event)
    local_occurred_at = timezone.template_localtime(event.occurred_at)

    return {
        "id": str(event.id),
        "siteId": str(event.site_id),
        "siteName": event.site.name,
        "type": event.event_type,
        "typeLabel": type_label,
        "displayName": display_name,
        "summary": _event_summary(
            event,
            display_name=display_name,
            location_label=location_label,
            operator_label=operator_label,
        ),
        "category": category,
        "categoryLabel": CATEGORY_LABELS.get(category, _humanize_event_value(category)),
        "severity": severity,
        "severityLabel": SEVERITY_LABELS.get(severity, _humanize_event_value(severity)),
        "occurredAtTime": local_occurred_at.strftime("%H:%M:%S"),
        "occurredAtDate": local_occurred_at.strftime("%d %b"),
        "subsystemName": event.subsystem.name if event.subsystem_id and event.subsystem else "",
        "zoneName": event.zone.name if event.zone_id and event.zone else "",
        "locationLabel": location_label,
        "operatorLabel": operator_label,
        "performedBy": operator_label,
        "hasPictures": has_pictures,
        "mediaCount": media_count,
        "normalizedType": normalized_type,
    }
