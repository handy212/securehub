from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("communication", "0004_broadcastmessageview"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcastmessage",
            name="send_push",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="broadcastmessage",
            name="send_email",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="broadcastmessage",
            name="send_sms",
            field=models.BooleanField(default=False),
        ),
    ]
