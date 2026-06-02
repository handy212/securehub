from django.core.management.base import BaseCommand, CommandError

from apps.hik_adapter.services import HikPartnerService


class Command(BaseCommand):
    help = "Import all Hik-Partner sites, then sync devices, subsystems, zones, and health."

    def add_arguments(self, parser):
        parser.add_argument(
            "--search",
            default="",
            help="Optional Hik site search term. Empty imports all visible sites.",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=100,
            help="Hik site/search page size.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of Hik sites to process.",
        )
        parser.add_argument(
            "--no-status",
            action="store_true",
            help="Only import sites/devices; skip transparent ISAPI subsystem and zone sync.",
        )
        parser.add_argument(
            "--no-health",
            action="store_true",
            help="Skip the site health report refresh after subsystem and zone sync.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List Hik sites that would be imported without writing local records.",
        )

    def handle(self, *args, **options):
        service = HikPartnerService()
        if not service.client.is_configured():
            raise CommandError("Hik-Partner Pro is not configured.")
        if service.client.dry_run and not options["dry_run"]:
            raise CommandError(
                "HIK_PARTNER_DRY_RUN is enabled. Re-run with --dry-run or disable dry-run."
            )

        result = service.import_hik_sites(
            search=options["search"],
            page_size=options["page_size"],
            limit=options["limit"],
            sync_status=not options["no_status"],
            refresh_health=not options["no_health"],
            dry_run=options["dry_run"],
            stdout=self.stdout,
        )

        for site in result["sites"]:
            if site.get("error"):
                self.stdout.write(
                    self.style.ERROR(
                        f"{site['name']} ({site['hik_site_id']}): {site['error']}"
                    )
                )
                continue
            marker = "created" if site["created"] else "updated"
            if options["dry_run"]:
                marker = "dry-run"
            self.stdout.write(
                f"{site['name']} ({site['hik_site_id']}): {marker}; "
                f"devices={site['devices_seen']} panels={site['synced_panels']} "
                f"status={'yes' if site['status_synced'] else 'no'} "
                f"health={'yes' if site['health_refreshed'] else 'no'}"
            )
            if site.get("health_warning"):
                self.stdout.write(self.style.WARNING(f"  health warning: {site['health_warning']}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Import complete: "
                f"hik_sites_seen={result['hik_sites_seen']} "
                f"created={result['created']} updated={result['updated']} "
                f"devices_seen={result['devices_seen']} synced_panels={result['synced_panels']} "
                f"status_synced={result['status_synced']} health_refreshed={result['health_refreshed']} "
                f"errors={result['errors']}"
            )
        )
