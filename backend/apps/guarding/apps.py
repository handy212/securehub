from django.apps import AppConfig


class GuardingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.guarding"
    verbose_name = "Guard Operations"

    def ready(self):
        from . import signals  # noqa: F401

