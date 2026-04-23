from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.alarms.models import AlarmEvent
from apps.sites.models import AlarmPanelDevice, CustomerSiteAccess, Site, Subsystem, Zone


class Command(BaseCommand):
    help = "Seed demo users, sites, devices, subsystems, zones, and an initial alarm event."

    OWNER_USERNAME = "owner"
    VIEWER_USERNAME = "viewer"
    DEMO_PASSWORD = "DemoPass123!"

    def handle(self, *args, **options):
        owner, _ = User.objects.get_or_create(
            username=self.OWNER_USERNAME,
            defaults={
                "email": "owner@example.com",
                "first_name": "Site",
                "last_name": "Owner",
            },
        )
        owner.set_password(self.DEMO_PASSWORD)
        owner.save(update_fields=["password"])

        viewer, _ = User.objects.get_or_create(
            username=self.VIEWER_USERNAME,
            defaults={
                "email": "viewer@example.com",
                "first_name": "Read",
                "last_name": "Only",
            },
        )
        viewer.set_password(self.DEMO_PASSWORD)
        viewer.save(update_fields=["password"])

        site, _ = Site.objects.get_or_create(
            hik_site_id="demo-site-001",
            defaults={
                "name": "Warehouse North",
                "address": "15 Industrial Estate",
                "city": "Manchester",
                "country": "UK",
            },
        )
        viewer_site, _ = Site.objects.get_or_create(
            hik_site_id="demo-site-002",
            defaults={
                "name": "Retail Showroom",
                "address": "211 River Street",
                "city": "Leeds",
                "country": "UK",
            },
        )

        CustomerSiteAccess.objects.get_or_create(
            user=owner,
            site=site,
            defaults={
                "role": CustomerSiteAccess.ROLE_OWNER,
                "can_control_alarm": True,
            },
        )
        CustomerSiteAccess.objects.get_or_create(
            user=viewer,
            site=viewer_site,
            defaults={
                "role": CustomerSiteAccess.ROLE_VIEWER,
                "can_control_alarm": False,
            },
        )

        device, _ = AlarmPanelDevice.objects.get_or_create(
            hik_device_id="demo-device-001",
            defaults={
                "site": site,
                "name": "Main Panel",
                "serial_number": "DEMO-SN-001",
                "is_online": True,
            },
        )
        subsystem, _ = Subsystem.objects.get_or_create(
            hik_subsystem_id="demo-subsystem-001",
            defaults={
                "site": site,
                "device": device,
                "name": "Main Warehouse",
                "subsystem_number": 1,
                "status": Subsystem.STATUS_DISARMED,
            },
        )
        zone, _ = Zone.objects.get_or_create(
            subsystem=subsystem,
            zone_number=1,
            defaults={
                "name": "Front Door",
                "state": Zone.STATE_NORMAL,
            },
        )

        AlarmEvent.objects.get_or_create(
            site=site,
            subsystem=subsystem,
            zone=zone,
            source_event_id="demo-event-001",
            defaults={
                "event_type": "system_ready",
                "payload": {"message": "Demo data initialized"},
                "occurred_at": site.created_at,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Login credentials:")
        self.stdout.write(f"{self.OWNER_USERNAME} / {self.DEMO_PASSWORD}")
        self.stdout.write(f"{self.VIEWER_USERNAME} / {self.DEMO_PASSWORD}")
