from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_populate_staff_operator_profiles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fcmdevice",
            name="platform",
            field=models.CharField(
                choices=[
                    ("android", "Android"),
                    ("ios", "iOS"),
                    ("web", "Web"),
                ],
                default="android",
                max_length=16,
            ),
        ),
    ]
