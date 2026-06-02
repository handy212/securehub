from django.db import migrations


def populate_operator_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    StaffOperatorProfile = apps.get_model("accounts", "StaffOperatorProfile")

    for user in User.objects.filter(is_staff=True):
        role = "platform_admin" if user.is_superuser else "operations"
        StaffOperatorProfile.objects.get_or_create(user=user, defaults={"role": role})


def reverse_populate(apps, schema_editor):
    StaffOperatorProfile = apps.get_model("accounts", "StaffOperatorProfile")
    StaffOperatorProfile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_staffoperatorprofile"),
    ]

    operations = [
        migrations.RunPython(populate_operator_profiles, reverse_populate),
    ]
