import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_customergroup"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffOperatorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("platform_admin", "Platform administrator"),
                            ("operations", "Operations"),
                            ("guarding", "Guarding"),
                            ("dispatcher", "Dispatcher"),
                            ("billing", "Billing"),
                            ("support", "Support"),
                            ("auditor", "Auditor (read-only)"),
                        ],
                        default="operations",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operator_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "staff operator profile",
                "verbose_name_plural": "staff operator profiles",
            },
        ),
    ]
