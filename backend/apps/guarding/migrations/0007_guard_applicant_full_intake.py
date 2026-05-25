# Generated manually for applicant form phases A–E

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("guarding", "0006_guardcredential_verified_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="guardapplicant",
            name="alternate_phone",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="assigned_branch",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="convicted_of_crime",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="conviction_explanation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="declaration_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="declaration_signature_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="declaration_signed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="emergency_contact_address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="emergency_contact_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="emergency_contact_phone",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="emergency_contact_relationship",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="gender",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="gps_address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="interview_score",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="marital_status",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="national_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="nationality",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="photo",
            field=models.ImageField(blank=True, upload_to="guard_applicants/photos/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="prior_security_experience",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="salary_expectation",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="guardapplicant",
            name="uniform_size",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.CreateModel(
            name="GuardApplicantDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("cv", "CV / Resume"),
                            ("national_id", "National ID"),
                            ("photo", "Passport Photo"),
                            ("certificate", "Certificate"),
                            ("police_clearance", "Police Clearance"),
                            ("reference_letter", "Reference Letter"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=32,
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("file", models.FileField(upload_to="guard_applicants/documents/%Y/%m/")),
                ("reference_number", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="guarding.guardapplicant",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_guard_applicant_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GuardApplicantEducation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("education_level", models.CharField(max_length=120)),
                ("institution_name", models.CharField(blank=True, max_length=160)),
                ("year_completed", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("certificates_obtained", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="education_records",
                        to="guarding.guardapplicant",
                    ),
                ),
            ],
            options={"ordering": ["-year_completed", "education_level"]},
        ),
        migrations.CreateModel(
            name="GuardApplicantEmployment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_name", models.CharField(max_length=160)),
                ("position", models.CharField(blank=True, max_length=120)),
                ("duties", models.TextField(blank=True)),
                ("supervisor_name", models.CharField(blank=True, max_length=120)),
                ("supervisor_contact", models.CharField(blank=True, max_length=64)),
                ("started_on", models.DateField(blank=True, null=True)),
                ("ended_on", models.DateField(blank=True, null=True)),
                ("years_experience", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("reason_for_leaving", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="employment_records",
                        to="guarding.guardapplicant",
                    ),
                ),
            ],
            options={"ordering": ["-started_on", "company_name"]},
        ),
        migrations.CreateModel(
            name="GuardApplicantReference",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("full_name", models.CharField(max_length=120)),
                ("company", models.CharField(blank=True, max_length=160)),
                ("position", models.CharField(blank=True, max_length=120)),
                ("phone_number", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="references",
                        to="guarding.guardapplicant",
                    ),
                ),
            ],
            options={"ordering": ["full_name"]},
        ),
        migrations.CreateModel(
            name="GuardApplicantProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("security_training_completed", models.BooleanField(default=False)),
                ("fire_safety_training", models.BooleanField(default=False)),
                ("first_aid_certification", models.BooleanField(default=False)),
                ("cctv_monitoring_experience", models.BooleanField(default=False)),
                ("access_control_experience", models.BooleanField(default=False)),
                ("driving_license_class", models.CharField(blank=True, max_length=32)),
                ("military_police_background", models.BooleanField(default=False)),
                ("height_cm", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("weight_kg", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("has_medical_condition", models.BooleanField(default=False)),
                ("medical_condition_notes", models.TextField(blank=True)),
                ("has_physical_disability", models.BooleanField(default=False)),
                ("physical_disability_notes", models.TextField(blank=True)),
                ("can_work_night_shifts", models.BooleanField(default=True)),
                ("can_stand_long_hours", models.BooleanField(default=True)),
                ("skill_communication", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("skill_report_writing", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("skill_computer", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("skill_radio", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("skill_conflict_resolution", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("available_start_date", models.DateField(blank=True, null=True)),
                ("preferred_location", models.CharField(blank=True, max_length=160)),
                (
                    "shift_preference",
                    models.CharField(
                        blank=True,
                        choices=[("day", "Day"), ("night", "Night"), ("rotational", "Rotational")],
                        max_length=24,
                    ),
                ),
                ("willing_to_travel", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "applicant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="guarding.guardapplicant",
                    ),
                ),
            ],
        ),
    ]
