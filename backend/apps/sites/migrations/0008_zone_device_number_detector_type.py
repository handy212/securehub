from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0007_zone_device_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="zone",
            name="device_number",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="zone",
            name="detector_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
