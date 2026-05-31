from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("guarding", "0008_guard_asset_management"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientportalaccess",
            name="can_view_guards",
            field=models.BooleanField(default=False),
        ),
    ]
