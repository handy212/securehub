# Generated migration for Subscription and SubscriptionPayment models

import datetime
import uuid
from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0003_remove_videodevice_site_delete_videochannel_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "monthly_rate",
                    models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
                ),
                (
                    "billing_day",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Day of the month the subscription is due (1–28).",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("overdue", "Overdue"),
                            ("suspended", "Suspended"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("next_due_date", models.DateField()),
                (
                    "grace_period_days",
                    models.PositiveSmallIntegerField(
                        default=7,
                        help_text="Days after due date before the subscription is automatically suspended.",
                    ),
                ),
                ("suspended_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "site",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to="sites.site",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SubscriptionPayment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("paid_at", models.DateTimeField(auto_now_add=True)),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="sites.subscription",
                    ),
                ),
            ],
        ),
    ]
