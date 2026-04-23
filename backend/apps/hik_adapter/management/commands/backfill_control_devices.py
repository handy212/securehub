from django.core.management.base import BaseCommand

from apps.alarms.models import AlarmEvent
from apps.hik_adapter.services import HikPartnerService
from apps.sites.models import AlarmPanelDevice


class Command(BaseCommand):
    help = "Backfill keyfobs, keypads, and card readers from stored alarm events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--device-serial",
            dest="device_serial",
            help="Limit the repair to a single panel serial.",
        )
        parser.add_argument(
            "--site-id",
            dest="site_id",
            help="Limit the repair to a single site UUID.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Maximum number of recent events to scan per run.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Inspect matching events without writing any inventory records.",
        )

    def handle(self, *args, **options):
        service = HikPartnerService()
        qs = AlarmEvent.objects.select_related("site").order_by("-occurred_at")

        device_serial = options.get("device_serial")
        site_id = options.get("site_id")
        if device_serial:
            qs = qs.filter(payload__deviceSerial=device_serial)
        if site_id:
            qs = qs.filter(site_id=site_id)

        scanned = 0
        repaired = 0
        for event in qs[: options["limit"]]:
            payload = event.payload or {}
            alarm_data = payload.get("alarmData") or {}
            cid_event = alarm_data.get("CIDEvent") or {}
            event_desc = cid_event.get("description") or alarm_data.get("eventDescription") or event.event_type
            event_desc_lower = str(cid_event.get("description") or event_desc or "").lower()
            performed_by = event.performed_by or cid_event.get("userName") or ""
            panel_serial = payload.get("deviceSerial") or alarm_data.get("deviceSerial") or ""
            panel = AlarmPanelDevice.objects.filter(serial_number=panel_serial).first()
            if not panel:
                continue

            if "exmodule" in event_desc_lower:
                scanned += 1
                if options["dry_run"]:
                    self.stdout.write(
                        f"[dry-run] {panel_serial} output_module from event {event.id} ({cid_event.get('deviceName') or event_desc})"
                    )
                    continue
                service._ensure_module_device_presence(
                    alarm_device=panel,
                    cid_event=cid_event,
                    performed_by=performed_by,
                )
                repaired += 1
                continue

            device_type = service._infer_control_device(event_desc, cid_event)
            if not device_type:
                continue

            scanned += 1
            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] {panel_serial} {device_type} from event {event.id} ({performed_by or event_desc})"
                )
                continue

            subsystem = event.subsystem
            service._ensure_control_device_presence(
                alarm_device=panel,
                subsystem=subsystem,
                device_type=device_type,
                cid_event=cid_event,
                performed_by=performed_by,
            )
            repaired += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Scanned {scanned} matching event(s); repaired {repaired} inventory record(s)."
            )
        )
