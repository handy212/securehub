from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communication", "0001_initial_broadcast_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcastmessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("billing", "Billing Notice"),
                    ("alert", "System Alert"),
                ],
                default="general",
                max_length=16,
            ),
        ),
    ]
