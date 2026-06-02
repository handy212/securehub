import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0017_subscriptionpayment_method_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="HikSiteDevice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("hik_device_id", models.CharField(max_length=128, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("serial_number", models.CharField(max_length=128, unique=True)),
                ("device_category", models.IntegerField(blank=True, null=True)),
                ("device_sub_category", models.IntegerField(blank=True, null=True)),
                ("device_type", models.CharField(blank=True, default="", max_length=128)),
                ("device_version", models.CharField(blank=True, default="", max_length=128)),
                ("is_online", models.BooleanField(default=False)),
                ("is_subscribed", models.BooleanField(default=False)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hik_devices",
                        to="sites.site",
                    ),
                ),
            ],
            options={
                "ordering": ["device_category", "name"],
            },
        ),
    ]
