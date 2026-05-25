import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("guarding", "0005_guardingprivacysettings_siteguarddispatchpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="guardcredential",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guardcredential",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_guard_credentials",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
