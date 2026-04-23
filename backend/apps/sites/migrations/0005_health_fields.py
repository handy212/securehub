from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0004_subscription_subscriptionpayment"),
    ]

    operations = [
        # AlarmPanelDevice health fields
        migrations.AddField(
            model_name="alarmpaneldevice",
            name="battery_status",
            field=models.CharField(default="unknown", max_length=16),
        ),
        migrations.AddField(
            model_name="alarmpaneldevice",
            name="work_status",
            field=models.CharField(default="unknown", max_length=16),
        ),
        migrations.AddField(
            model_name="alarmpaneldevice",
            name="cloud_status",
            field=models.CharField(default="unknown", max_length=16),
        ),
        migrations.AddField(
            model_name="alarmpaneldevice",
            name="last_health_check",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Zone health fields
        migrations.AddField(
            model_name="zone",
            name="low_battery",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="zone",
            name="tamper",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="zone",
            name="signal_strength",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
    ]
