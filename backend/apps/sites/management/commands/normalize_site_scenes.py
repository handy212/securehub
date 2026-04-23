from django.core.management.base import BaseCommand

from apps.sites.models import Site
from apps.sites.scenes import normalize_scene_label


class Command(BaseCommand):
    help = "Normalize legacy site scene values to the supported scene list."

    def handle(self, *args, **options):
        updated = 0

        for site in Site.objects.exclude(primary_industry=""):
            normalized = normalize_scene_label(site.primary_industry)
            if normalized and normalized != site.primary_industry:
                site.primary_industry = normalized
                site.save(update_fields=["primary_industry", "updated_at"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Normalized {updated} site scene value(s)."))
