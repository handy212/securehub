from __future__ import annotations

import logging

import requests

from apps.alarms.models import AlarmEvent

logger = logging.getLogger(__name__)


IMAGE_CONTENT_TYPES = ("image/",)
VIDEO_CONTENT_TYPES = ("video/",)
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif")


def _alarm_data(payload: dict) -> dict:
    alarm_data = payload.get("alarmData") or {}
    return alarm_data if isinstance(alarm_data, dict) else {}


def _event_has_video_flag(alarm_data: dict) -> bool:
    value = alarm_data.get("isVideo")
    return str(value).strip().lower() in {"1", "2", "true", "yes"}


def _stored_picture_entries(payload: dict) -> list[dict]:
    pictures = payload.get("pictures") or []
    if pictures:
        return [pic for pic in pictures if isinstance(pic, dict)]

    alarm_data = _alarm_data(payload)
    entries = []
    for pic in alarm_data.get("pictureList", []):
        if not isinstance(pic, dict):
            continue
        url = pic.get("url", "")
        if not url:
            continue
        entries.append(
            {
                "id": pic.get("id", ""),
                "url": url,
                "needs_url_fetch": url.startswith("ISAPI_FILES"),
                "type": pic.get("type", ""),
            }
        )
    return entries


def collect_related_event_media(event: AlarmEvent) -> list[dict]:
    payload = event.payload or {}
    alarm_data = _alarm_data(payload)
    relation_id = alarm_data.get("relationId")

    related_events = [event]
    if relation_id:
        siblings = (
            AlarmEvent.objects.filter(site=event.site, payload__alarmData__relationId=relation_id)
            .exclude(id=event.id)
            .order_by("occurred_at", "id")
        )
        related_events.extend(siblings)

    resolved = []
    seen_keys: set[str] = set()
    for related_event in related_events:
        related_payload = related_event.payload or {}
        related_alarm_data = _alarm_data(related_payload)
        for picture in _stored_picture_entries(related_payload):
            media_id = picture.get("id", "") or ""
            url = picture.get("url", "") or ""
            if not url:
                continue
            dedupe_key = media_id or url
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            resolved.append(
                {
                    "id": media_id,
                    "url": url,
                    "needs_url_fetch": bool(picture.get("needs_url_fetch")) or url.startswith("ISAPI_FILES"),
                    "type": picture.get("type", ""),
                    "alarm_data": related_alarm_data,
                    "source_event_id": str(related_event.id),
                }
            )
    return resolved


def probe_remote_media_type(url: str, *, timeout: int = 10) -> str | None:
    if not url or not url.startswith(("http://", "https://")):
        return None

    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type.startswith(VIDEO_CONTENT_TYPES):
            return "video"
        if content_type.startswith(IMAGE_CONTENT_TYPES):
            return "image"
    except requests.RequestException as exc:
        logger.debug("Media HEAD probe failed for %s: %s", url, exc)

    try:
        response = requests.get(url, stream=True, allow_redirects=True, timeout=timeout)
        content_type = (response.headers.get("Content-Type") or "").lower()
        response.close()
        if content_type.startswith(VIDEO_CONTENT_TYPES):
            return "video"
        if content_type.startswith(IMAGE_CONTENT_TYPES):
            return "image"
    except requests.RequestException as exc:
        logger.debug("Media GET probe failed for %s: %s", url, exc)

    return None


def resolve_picture_media_type(
    *,
    url: str,
    media_id: str = "",
    stored_type: str = "",
    alarm_data: dict | None = None,
    probe_remote: bool = False,
) -> str:
    lowered_url = str(url or "").lower()
    lowered_type = str(stored_type or "").strip().lower()
    alarm_data = alarm_data or {}

    if lowered_type == "video":
        return "video"
    if ".mp4" in lowered_url or "isdevvideo=1" in lowered_url or "-2-" in media_id or "-2-" in lowered_url:
        return "video"
    if _event_has_video_flag(alarm_data):
        return "video"

    if any(lowered_url.endswith(suffix) for suffix in IMAGE_SUFFIXES):
        return "image"

    if probe_remote:
        probed_type = probe_remote_media_type(url)
        if probed_type:
            return probed_type

    if lowered_type == "image":
        return "image"

    return "image"
