from django.apps import AppConfig


class AlarmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.alarms"

    def ready(self):
        import apps.alarms.checks  # noqa: F401
        from django.conf import settings

        if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
            from django.db.backends.signals import connection_created

            def _set_sqlite_wal(sender, connection, **kwargs):
                if connection.vendor == "sqlite":
                    with connection.cursor() as cursor:
                        cursor.execute("PRAGMA journal_mode=WAL;")
                        cursor.execute("PRAGMA synchronous=NORMAL;")

            connection_created.connect(_set_sqlite_wal)
