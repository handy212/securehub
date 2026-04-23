"""
Management command: link_real_site
-----------------------------------
Creates (or updates) a Site record pointing at a real Hikvision site,
assigns it to an existing user, and optionally runs a device sync.

Usage:
    python manage.py link_real_site \\
        --hik-site-id <HIK_SITE_ID> \\
        --hik-device-id <HIK_DEVICE_ID> \\
        --device-serial <SERIAL> \\
        --username owner \\
        --site-name "Head Office" \\
        [--sync]
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.sites.models import AlarmPanelDevice, CustomerSiteAccess, Site


class Command(BaseCommand):
    help = "Link a real Hikvision site to a local user account."

    def add_arguments(self, parser):
        parser.add_argument("--hik-site-id", required=True)
        parser.add_argument("--hik-device-id", required=True)
        parser.add_argument("--device-serial", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--site-name", default="")
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run device sync against Hik-Partner Pro after linking.",
        )

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"User '{options['username']}' not found. Run seed_demo first.")

        site_name = options["site_name"] or f"Site {options['hik_site_id']}"

        site, created = Site.objects.update_or_create(
            hik_site_id=options["hik_site_id"],
            defaults={"name": site_name, "is_active": True},
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(f"{verb} site: {site.name} (id={site.id})")

        CustomerSiteAccess.objects.get_or_create(
            user=user,
            site=site,
            defaults={
                "role": CustomerSiteAccess.ROLE_OWNER,
                "can_control_alarm": True,
            },
        )
        self.stdout.write(f"Access granted: {user.username} → {site.name}")

        device, _ = AlarmPanelDevice.objects.update_or_create(
            hik_device_id=options["hik_device_id"],
            defaults={
                "site": site,
                "name": f"Panel {options['device_serial']}",
                "serial_number": options["device_serial"],
                "is_online": True,
            },
        )
        self.stdout.write(f"Alarm panel: {device.name} (serial={device.serial_number})")

        if options["sync"]:
            from apps.hik_adapter.services import HikPartnerService
            result = HikPartnerService().sync_site_devices(site)
            self.stdout.write(self.style.SUCCESS(f"Sync result: {result}"))

        self.stdout.write(self.style.SUCCESS("\nDone. Site ID for API calls:"))
        self.stdout.write(str(site.id))
