# Generated manually for guard asset management

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("guarding", "0007_guard_applicant_full_intake"),
        ("sites", "0019_merge_0018_hiksitedevice_0018_subscriptionpackage_emergency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GuardAssetType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160)),
                ("code", models.CharField(max_length=64, unique=True)),
                ("category", models.CharField(choices=[("radio", "Radio"), ("keys", "Keys"), ("uniform", "Uniform"), ("weapon_accessory", "Weapon accessory"), ("vehicle", "Vehicle"), ("other", "Other")], db_index=True, default="other", max_length=32)),
                ("tracking_mode", models.CharField(choices=[("serial", "Serial"), ("quantity", "Quantity")], default="serial", max_length=16)),
                ("requires_return", models.BooleanField(default=True)),
                ("default_condition_check", models.BooleanField(default=True)),
                ("replacement_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="GuardAssetDepot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("site", models.ForeignKey(blank=True, help_text="Leave blank for central / organization-wide depot.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="guard_asset_depots", to="sites.site")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="GuardAssetUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("asset_tag", models.CharField(db_index=True, max_length=80, unique=True)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("available", "Available"), ("issued", "Issued"), ("maintenance", "Maintenance"), ("retired", "Retired"), ("lost", "Lost")], db_index=True, default="available", max_length=24)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="units", to="guarding.guardassettype")),
                ("depot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="units", to="guarding.guardassetdepot")),
                ("site", models.ForeignKey(blank=True, help_text="Optional restriction: unit only issuable for this site.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="guard_asset_units", to="sites.site")),
            ],
            options={"ordering": ["asset_tag"]},
        ),
        migrations.AddIndex(
            model_name="guardassetunit",
            index=models.Index(fields=["asset_type", "status"], name="guard_asset_unit_type_st_idx"),
        ),
        migrations.CreateModel(
            name="GuardAssetStock",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity_on_hand", models.PositiveIntegerField(default=0)),
                ("quantity_reserved", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_levels", to="guarding.guardassettype")),
                ("depot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_levels", to="guarding.guardassetdepot")),
            ],
            options={"ordering": ["depot__name", "asset_type__name"], "unique_together": {("asset_type", "depot")}},
        ),
        migrations.CreateModel(
            name="GuardAssetMaintenanceLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status_before", models.CharField(blank=True, max_length=24)),
                ("status_after", models.CharField(blank=True, max_length=24)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="guard_asset_maintenance_logs", to=settings.AUTH_USER_MODEL)),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maintenance_logs", to="guarding.guardassetunit")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="GuardingAssetPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(default=True)),
                ("default_mode", models.CharField(choices=[("advisory", "Advisory"), ("strict", "Strict")], default="advisory", max_length=16)),
                ("enforce_issue_before_clock_in", models.BooleanField(default=True)),
                ("enforce_return_before_clock_out", models.BooleanField(default=True)),
                ("allow_supervisor_override", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("post", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="asset_policy", to="guarding.guardpost")),
                ("site", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="guarding_asset_policy", to="sites.site")),
            ],
            options={"verbose_name_plural": "Guarding asset policies"},
        ),
        migrations.AddConstraint(
            model_name="guardingassetpolicy",
            constraint=models.CheckConstraint(
                check=models.Q(("site__isnull", False), ("post__isnull", True))
                | models.Q(("site__isnull", True), ("post__isnull", False)),
                name="guard_asset_policy_site_xor_post",
            ),
        ),
        migrations.CreateModel(
            name="PostAssetKit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_kits", to="guarding.guardpost")),
            ],
            options={"ordering": ["post__name", "name"]},
        ),
        migrations.CreateModel(
            name="PostAssetKitLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity_required", models.PositiveSmallIntegerField(default=1)),
                ("is_optional", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="kit_lines", to="guarding.guardassettype")),
                ("kit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="guarding.postassetkit")),
            ],
            options={"ordering": ["kit", "asset_type__name"], "unique_together": {("kit", "asset_type")}},
        ),
        migrations.CreateModel(
            name="ShiftAssetManifest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("issued", "Issued"), ("partial_return", "Partial return"), ("closed", "Closed"), ("exception", "Exception")], db_index=True, default="draft", max_length=24)),
                ("enforcement_mode", models.CharField(choices=[("advisory", "Advisory"), ("strict", "Strict")], default="advisory", max_length=16)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("guard_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("override_clock_in", models.BooleanField(default=False)),
                ("override_clock_out", models.BooleanField(default=False)),
                ("override_at", models.DateTimeField(blank=True, null=True)),
                ("override_reason", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="asset_manifest", to="guarding.shiftassignment")),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="closed_shift_asset_manifests", to=settings.AUTH_USER_MODEL)),
                ("depot", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="manifests", to="guarding.guardassetdepot")),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="issued_shift_asset_manifests", to=settings.AUTH_USER_MODEL)),
                ("override_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="overridden_shift_asset_manifests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ShiftAssetManifestLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("expected_qty", models.PositiveSmallIntegerField(default=1)),
                ("issued_qty", models.PositiveSmallIntegerField(default=0)),
                ("returned_qty", models.PositiveSmallIntegerField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("issued", "Issued"), ("returned", "Returned"), ("lost", "Lost"), ("damaged", "Damaged"), ("not_required", "Not required")], db_index=True, default="pending", max_length=24)),
                ("condition_out", models.CharField(blank=True, max_length=120)),
                ("condition_in", models.CharField(blank=True, max_length=120)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("returned_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="manifest_lines", to="guarding.guardassettype")),
                ("asset_unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="manifest_lines", to="guarding.guardassetunit")),
                ("manifest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="guarding.shiftassetmanifest")),
            ],
            options={"ordering": ["manifest", "asset_type__name"]},
        ),
    ]
