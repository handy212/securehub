from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0006_add_sub_category_delay_charge_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="zone",
            name="device_type",
            field=models.CharField(default="zone", max_length=16),
        ),
        migrations.AlterUniqueTogether(
            name="zone",
            unique_together={("subsystem", "zone_number", "device_type")},
        ),
    ]
