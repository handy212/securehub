import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_customergroup"),
        ("communication", "0002_broadcastmessage_message_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcastmessage",
            name="recipient_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="broadcast_messages",
                to="accounts.customergroup",
            ),
        ),
    ]
