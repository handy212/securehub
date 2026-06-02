import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0019_merge_0018_hiksitedevice_0018_subscriptionpackage_emergency"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationsZone",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("color", models.CharField(default="#6366f1", max_length=7)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "operations zone",
                "verbose_name_plural": "operations zones",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="site",
            name="operations_zone",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sites",
                to="sites.operationszone",
            ),
        ),
    ]
