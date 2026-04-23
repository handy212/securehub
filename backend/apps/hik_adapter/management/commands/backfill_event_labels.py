from django.core.management.base import BaseCommand

from apps.alarms.models import AlarmEvent
from apps.hik_adapter.services import HikPartnerService


class Command(BaseCommand):
    help = "Backfill friendly display labels, normalized types, category, and severity for stored Hik events."

    def add_arguments(self, parser):
        parser.add_argument("--site-id", dest="site_id", help="Limit to one site UUID.")
        parser.add_argument("--device-serial", dest="device_serial", help="Limit to one panel serial.")
        parser.add_argument("--limit", type=int, default=1000, help="Maximum number of recent events to inspect.")

    def handle(self, *args, **options):
        service = HikPartnerService()
        qs = AlarmEvent.objects.order_by("-occurred_at")

        if options.get("site_id"):
            qs = qs.filter(site_id=options["site_id"])
        if options.get("device_serial"):
            qs = qs.filter(payload__deviceSerial=options["device_serial"])

        updated = 0
        inspected = 0

        for event in qs[: options["limit"]]:
            inspected += 1
            payload = dict(event.payload or {})
            alarm_data = payload.get("alarmData") or {}
            cid_event = alarm_data.get("CIDEvent") or {}
            raw_event_type = (
                payload.get("raw_event_type")
                or alarm_data.get("eventType")
                or event.event_code
                or event.event_type
            )
            event_desc = (
                cid_event.get("description")
                or alarm_data.get("eventDescription")
                or event.event_type
            )

            metadata = service._get_event_metadata(raw_event_type=raw_event_type, event_desc=event_desc)
            display_name = metadata["display_name"]
            normalized = metadata["normalized"]

            changed = False
            if payload.get("event_name") != display_name:
                payload["event_name"] = display_name
                changed = True
            if payload.get("normalized_event_type") != normalized:
                payload["normalized_event_type"] = normalized
                changed = True
            if payload.get("raw_event_type") != raw_event_type:
                payload["raw_event_type"] = raw_event_type
                changed = True
            if event.event_category != metadata["category"]:
                event.event_category = metadata["category"]
                changed = True
            if event.severity != metadata["severity"]:
                event.severity = metadata["severity"]
                changed = True

            if changed:
                event.payload = payload
                event.save(update_fields=["payload", "event_category", "severity"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Inspected {inspected} event(s); updated {updated} event record(s)."
            )
        )
