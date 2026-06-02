"""Staff console views for subscriptions and billing."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, View

from apps.alarms.event_labels import humanize_event_label
from apps.alarms.models import AlarmEvent as Event
from apps.alarms.tasks import (
    send_reactivation_notice,
    send_subscription_lockout_notice,
    send_suspension_notice,
)
from apps.dashboard.billing_helpers import (
    billing_day_from_due_date,
    parse_payment_method,
    validate_reactivation_due_date,
    validate_subscription_payment_window,
)
from apps.dashboard.parsers import parse_date_field, parse_decimal_field, parse_int_field
from apps.dashboard.permissions import StaffRequiredMixin
from apps.emergency.models import (
    AccountEmergencyService,
    EmergencyServicePlan,
    EmergencyServiceStatus,
    SiteEmergencyService,
)
from apps.sites.models import Site, Subscription, SubscriptionPackage, SubscriptionPayment

class SubscriptionListView(StaffRequiredMixin, ListView):
    model = Subscription
    template_name = "dashboard/billing/subscriptions.html"
    context_object_name = "subscriptions"
    ordering = ["status", "next_due_date"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("site", "package")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unsubscribed_sites"] = Site.objects.filter(
            subscription__isnull=True
        ).order_by("name")
        context["current_status"] = self.request.GET.get("status", "")
        today = timezone.localdate()
        context["today"] = today
        context["count_active"] = Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).count()
        context["count_overdue"] = Subscription.objects.filter(status=Subscription.STATUS_OVERDUE).count()
        context["count_suspended"] = Subscription.objects.filter(status=Subscription.STATUS_SUSPENDED).count()
        context["total_mrr"] = (
            Subscription.objects.filter(status=Subscription.STATUS_ACTIVE)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        emergency_active_statuses = [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]
        context["emergency_site_mrr"] = (
            SiteEmergencyService.objects.filter(status__in=emergency_active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["emergency_account_mrr"] = (
            AccountEmergencyService.objects.filter(status__in=emergency_active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["emergency_total_mrr"] = context["emergency_site_mrr"] + context["emergency_account_mrr"]
        context["combined_mrr"] = context["total_mrr"] + context["emergency_total_mrr"]
        recent_payments = list(
            SubscriptionPayment.objects.select_related("subscription__site", "recorded_by")
            .order_by("-paid_at")[:20]
        )
        context["recent_payments"] = recent_payments
        context["total_collected_recent"] = sum(p.amount for p in recent_payments)
        for sub in context["subscriptions"]:
            days_delta = (today - sub.next_due_date).days
            setattr(sub, "days_delta", days_delta)
            pct = 0
            if sub.status == Subscription.STATUS_OVERDUE and sub.grace_period_days > 0:
                pct = min(100, int((days_delta / sub.grace_period_days) * 100))
            setattr(sub, "grace_pct", pct)
            setattr(sub, "grace_bar_color", "bg-red-500" if pct >= 80 else "bg-amber-400")
            setattr(sub, "days_until_due", abs(days_delta))
            try:
                emergency_service = sub.site.emergency_service
            except SiteEmergencyService.DoesNotExist:
                emergency_service = None
            setattr(sub, "emergency_service", emergency_service)
        pkgs = SubscriptionPackage.objects.filter(is_active=True).order_by("monthly_rate")
        context["packages"] = pkgs
        context["packages_json"] = json.dumps([
            {
                "id": str(p.id),
                "rate": str(p.monthly_rate),
                "grace": p.grace_period_days,
                "emergency": p.includes_emergency_service,
                "emergencyRate": str(p.emergency_monthly_rate),
            }
            for p in pkgs
        ])
        context["emergency_statuses"] = EmergencyServiceStatus.choices
        context["active_emergency_plans"] = EmergencyServicePlan.objects.filter(is_active=True).order_by("monthly_rate")
        return context


def sync_site_emergency_addon_from_subscription_request(request, *, site, subscription_status):
    enabled = request.POST.get("emergency_enabled") == "1"
    existing = SiteEmergencyService.objects.filter(site=site).first()
    if not enabled:
        if existing:
            existing.status = EmergencyServiceStatus.CANCELLED
            existing.save(update_fields=["status", "updated_at"])
        return existing

    emergency_rate = request.POST.get("emergency_monthly_rate", "").strip()
    if not emergency_rate:
        raise ValueError("Emergency add-on rate is required when patrol support is enabled.")
    status = request.POST.get("emergency_status", "").strip() or subscription_status
    valid_statuses = {choice[0] for choice in EmergencyServiceStatus.choices}
    if status not in valid_statuses:
        raise ValueError("Please choose a valid emergency add-on status.")
    parsed_rate = parse_decimal_field(
        emergency_rate,
        label="Emergency add-on rate",
        min_value=Decimal("0.00"),
    )
    defaults = {
        "monthly_rate": parsed_rate,
        "status": status,
        "next_due_date": parse_date_field(request.POST.get("next_due_date", ""), label="Next due date"),
        "notes": request.POST.get("emergency_notes", "").strip(),
    }
    service, _ = SiteEmergencyService.objects.update_or_create(site=site, defaults=defaults)
    return service


def sync_site_emergency_addon_lifecycle(subscription, *, next_due_date=None, status=None):
    service = SiteEmergencyService.objects.filter(site=subscription.site).first()
    if service is None:
        return None
    update_fields = ["updated_at"]
    if next_due_date is not None:
        service.next_due_date = next_due_date
        update_fields.append("next_due_date")
    if status is not None:
        service.status = status
        update_fields.append("status")
    service.save(update_fields=update_fields)
    return service


class CreateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request):
        site_id = request.POST.get("site_id")
        package_id = request.POST.get("package_id", "").strip()
        monthly_rate = request.POST.get("monthly_rate")
        billing_day = request.POST.get("billing_day", "1")
        grace_period_days = request.POST.get("grace_period_days", "7")
        next_due_date = request.POST.get("next_due_date")
        notes = request.POST.get("notes", "")

        if not site_id or not monthly_rate or not next_due_date:
            messages.error(request, "Site, monthly rate, and next due date are required.")
            return redirect("dashboard:subscriptions")

        site = get_object_or_404(Site, pk=site_id)

        if Subscription.objects.filter(site=site).exists():
            messages.error(request, f"'{site.name}' already has a subscription.")
            return redirect("dashboard:subscriptions")

        package = None
        if package_id:
            package = SubscriptionPackage.objects.filter(pk=package_id).first()

        try:
            parsed_rate = parse_decimal_field(
                monthly_rate,
                label="Monthly rate",
                min_value=Decimal("0.00"),
            )
            parsed_billing_day = parse_int_field(
                billing_day,
                label="Billing day",
                min_value=1,
                max_value=28,
            )
            parsed_grace_days = parse_int_field(
                grace_period_days,
                label="Grace period",
                min_value=0,
                max_value=30,
            )
            parsed_due_date = parse_date_field(next_due_date, label="Next due date")
            status = Subscription.classify_status(
                next_due_date=parsed_due_date,
                grace_period_days=parsed_grace_days,
            )
            subscription = Subscription.objects.create(
                site=site,
                monthly_rate=parsed_rate,
                billing_day=parsed_billing_day,
                grace_period_days=parsed_grace_days,
                next_due_date=parsed_due_date,
                notes=notes,
                status=status,
                package=package,
                suspended_at=timezone.now() if status == Subscription.STATUS_SUSPENDED else None,
            )
            sync_site_emergency_addon_from_subscription_request(
                request,
                site=site,
                subscription_status=subscription.status,
            )
            messages.success(request, f"Subscription created for '{site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Failed to create subscription: {exc}")

        return redirect("dashboard:subscriptions")


class UpdateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        try:
            sub.monthly_rate = parse_decimal_field(
                request.POST.get("monthly_rate", ""),
                label="Monthly rate",
                min_value=Decimal("0.00"),
            )
            sub.billing_day = parse_int_field(
                request.POST.get("billing_day", ""),
                label="Billing day",
                min_value=1,
                max_value=28,
            )
            sub.grace_period_days = parse_int_field(
                request.POST.get("grace_period_days", ""),
                label="Grace period",
                min_value=0,
                max_value=30,
            )
            sub.next_due_date = parse_date_field(
                request.POST.get("next_due_date", ""),
                label="Next due date",
            )
            sub.notes = request.POST.get("notes", "").strip()
            package_id = request.POST.get("package_id", "").strip()
            sub.package = SubscriptionPackage.objects.filter(pk=package_id).first() if package_id else None
            sub.apply_due_date_status()
            sub.save()
            sync_site_emergency_addon_from_subscription_request(
                request,
                site=sub.site,
                subscription_status=sub.status,
            )
            messages.success(request, f"Subscription for '{sub.site.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:subscriptions")


class UpdateSubscriptionPaymentView(StaffRequiredMixin, View):
    def post(self, request, payment_id):
        payment = get_object_or_404(SubscriptionPayment, pk=payment_id)
        try:
            original_period_end = payment.period_end
            subscription = payment.subscription
            current_due_anchored_to_payment = (
                subscription.next_due_date == original_period_end + timedelta(days=1)
            )

            payment.amount = parse_decimal_field(
                request.POST.get("amount", ""),
                label="Amount",
                min_value=Decimal("0.01"),
            )
            parsed_period_start = parse_date_field(
                request.POST.get("period_start", ""),
                label="Period start",
            )
            parsed_period_end = parse_date_field(
                request.POST.get("period_end", ""),
                label="Period end",
            )
            if parsed_period_end < parsed_period_start:
                raise ValueError("Period end must be on or after period start.")
            validate_subscription_payment_window(
                subscription,
                period_start=parsed_period_start,
                period_end=parsed_period_end,
                exclude_payment_id=payment.pk,
            )
            payment.period_start = parsed_period_start
            payment.period_end = parsed_period_end
            payment.method = parse_payment_method(request.POST.get("method", ""))
            payment.reference = request.POST.get("reference", "").strip()
            payment.notes = request.POST.get("notes", "").strip()
            payment.save()

            latest_payment = subscription.payments.order_by("-period_end", "-paid_at").first()
            if (
                subscription.status != Subscription.STATUS_CANCELLED
                and latest_payment is not None
                and (latest_payment.pk == payment.pk or current_due_anchored_to_payment)
            ):
                subscription.sync_next_due_date_from_latest_payment()
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            messages.success(request, "Payment record updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:subscriptions")


class DeleteSubscriptionPaymentView(StaffRequiredMixin, View):
    def post(self, request, payment_id):
        payment = get_object_or_404(SubscriptionPayment, pk=payment_id)
        site_name = payment.subscription.site.name
        subscription = payment.subscription
        current_due_anchored_to_payment = (
            subscription.next_due_date == payment.period_end + timedelta(days=1)
        )
        deleted_period_start = payment.period_start
        payment.delete()

        if subscription.status != Subscription.STATUS_CANCELLED and current_due_anchored_to_payment:
            if subscription.sync_next_due_date_from_latest_payment():
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            else:
                subscription.next_due_date = deleted_period_start
                subscription.apply_due_date_status()
                subscription.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
        messages.success(request, f"Payment record for '{site_name}' deleted.")
        return redirect("dashboard:subscriptions")


class RecordPaymentView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        amount = request.POST.get("amount")
        period_start = request.POST.get("period_start")
        period_end = request.POST.get("period_end")
        method = request.POST.get("method", "").strip()
        reference = request.POST.get("reference", "").strip()
        notes = request.POST.get("notes", "")

        if not amount or not period_start or not period_end:
            messages.error(request, "Amount, period start, and period end are required.")
            return redirect("dashboard:subscriptions")

        try:
            parsed_amount = parse_decimal_field(
                amount,
                label="Amount",
                min_value=Decimal("0.01"),
            )
            parsed_start = parse_date_field(period_start, label="Period start")
            parsed_end = parse_date_field(period_end, label="Period end")
            if parsed_end < parsed_start:
                raise ValueError("Period end must be on or after period start.")
            validate_subscription_payment_window(
                sub,
                period_start=parsed_start,
                period_end=parsed_end,
            )
            SubscriptionPayment.objects.create(
                subscription=sub,
                amount=parsed_amount,
                period_start=parsed_start,
                period_end=parsed_end,
                method=parse_payment_method(method),
                reference=reference,
                notes=notes,
                recorded_by=request.user,
            )
            new_due = parsed_end + timedelta(days=1)
            sub.next_due_date = new_due
            sub.apply_due_date_status()
            sub.save(update_fields=["next_due_date", "status", "suspended_at", "updated_at"])
            sync_site_emergency_addon_lifecycle(
                sub,
                next_due_date=new_due,
                status=EmergencyServiceStatus.ACTIVE if sub.status == Subscription.STATUS_ACTIVE else sub.status,
            )
            messages.success(request, f"Payment recorded for '{sub.site.name}'. Next due: {new_due}.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Failed to record payment: {exc}")

        return redirect("dashboard:subscriptions")


class SuspendSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        if sub.status == Subscription.STATUS_SUSPENDED:
            messages.info(request, f"'{sub.site.name}' subscription is already suspended.")
            return redirect("dashboard:site-console", pk=sub.site.pk)
        else:
            sub.suspend()
            sync_site_emergency_addon_lifecycle(sub, status=EmergencyServiceStatus.SUSPENDED)
            send_suspension_notice.delay(str(sub.id))
            # Log the lockdown as a system event
            Event.objects.create(
                site=sub.site,
                event_type="SITE_LOCKED",
                occurred_at=timezone.now(),
                payload={
                    "event_name": humanize_event_label("SITE_LOCKED"),
                    "normalized_event_type": "site_locked",
                    "reason": "Operator Lockdown",
                    "admin": request.user.username,
                    "message": "Access restricted by dealer operator."
                }
            )
            messages.warning(request, f"Subscription for '{sub.site.name}' has been suspended. Client access is now blocked.")
            return redirect("dashboard:site-console", pk=sub.site.pk)


class CancelSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        if sub.status == Subscription.STATUS_CANCELLED:
            messages.info(request, f"'{sub.site.name}' subscription is already cancelled.")
            return redirect("dashboard:subscriptions")

        sub.status = Subscription.STATUS_CANCELLED
        sub.suspended_at = timezone.now()
        sub.save(update_fields=["status", "suspended_at", "updated_at"])
        sync_site_emergency_addon_lifecycle(sub, status=EmergencyServiceStatus.CANCELLED)
        send_subscription_lockout_notice.delay(str(sub.id), notice_type="cancelled")
        Event.objects.create(
            site=sub.site,
            event_type="SITE_CANCELLED",
            occurred_at=timezone.now(),
            payload={
                "event_name": humanize_event_label("SITE_CANCELLED"),
                "normalized_event_type": "site_cancelled",
                "reason": "Subscription Cancelled",
                "admin": request.user.username,
                "message": "Billing plan cancelled by operator.",
            },
        )
        messages.warning(request, f"Subscription for '{sub.site.name}' cancelled.")
        return redirect("dashboard:subscriptions")


class ReactivateSubscriptionView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        next_due = request.POST.get("next_due_date")
        try:
            new_due = parse_date_field(next_due, label="Next due date") if next_due else None
            if new_due is not None:
                validate_reactivation_due_date(sub, new_due)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:site-console", pk=sub.site.pk)

        sub.reactivate(new_due_date=new_due)
        if sub.status != Subscription.STATUS_ACTIVE:
            messages.error(request, "Reactivation did not restore access. Please choose a current or future due date.")
            return redirect("dashboard:site-console", pk=sub.site.pk)
        sync_site_emergency_addon_lifecycle(
            sub,
            next_due_date=sub.next_due_date,
            status=EmergencyServiceStatus.ACTIVE,
        )
        send_reactivation_notice.delay(str(sub.id))
        # Log the reactivation as a system event
        Event.objects.create(
            site=sub.site,
            event_type="SITE_RESTORED",
            occurred_at=timezone.now(),
            payload={
                "event_name": humanize_event_label("SITE_RESTORED"),
                "normalized_event_type": "site_restored",
                "reason": "Operator Reactivation",
                "admin": request.user.username,
                "message": "Access restored by dealer operator."
            }
        )
        messages.success(request, f"Subscription for '{sub.site.name}' reactivated. Next due: {sub.next_due_date}.")
        return redirect("dashboard:site-console", pk=sub.site.pk)


# ---------------------------------------------------------------------------
# Subscription Packages
# ---------------------------------------------------------------------------

class SubscriptionPackageListView(StaffRequiredMixin, View):
    template_name = "dashboard/billing/packages.html"

    def get(self, request):
        packages = SubscriptionPackage.objects.all()
        emergency_mrr = (
            SiteEmergencyService.objects.filter(status__in=[EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE])
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        return render(
            request,
            self.template_name,
            {"packages": packages, "emergency_mrr": emergency_mrr},
        )

    def post(self, request):
        name = request.POST.get("name", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        grace_period_days = request.POST.get("grace_period_days", "7").strip()
        description = request.POST.get("description", "").strip()
        includes_emergency = request.POST.get("includes_emergency_service") == "on"
        emergency_rate = request.POST.get("emergency_monthly_rate", "0").strip() or "0"

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            parsed_rate = parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            parsed_grace = parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            parsed_emergency_rate = parse_decimal_field(emergency_rate, label="Emergency add-on rate", min_value=Decimal("0.00"))
            SubscriptionPackage.objects.create(
                name=name,
                monthly_rate=parsed_rate,
                includes_emergency_service=includes_emergency,
                emergency_monthly_rate=parsed_emergency_rate,
                grace_period_days=parsed_grace,
                description=description,
            )
            messages.success(request, f"Package '{name}' created.")
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect("dashboard:packages")


class UpdateSubscriptionPackageView(StaffRequiredMixin, View):
    def post(self, request, pk):
        pkg = get_object_or_404(SubscriptionPackage, pk=pk)
        name = request.POST.get("name", "").strip()
        monthly_rate = request.POST.get("monthly_rate", "").strip()
        grace_period_days = request.POST.get("grace_period_days", "").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") == "on"
        includes_emergency = request.POST.get("includes_emergency_service") == "on"
        emergency_rate = request.POST.get("emergency_monthly_rate", "0").strip() or "0"

        if not name or not monthly_rate:
            messages.error(request, "Name and monthly rate are required.")
            return redirect("dashboard:packages")

        try:
            pkg.name = name
            pkg.monthly_rate = parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00"))
            pkg.grace_period_days = parse_int_field(grace_period_days, label="Grace period", min_value=0, max_value=90)
            pkg.includes_emergency_service = includes_emergency
            pkg.emergency_monthly_rate = parse_decimal_field(emergency_rate, label="Emergency add-on rate", min_value=Decimal("0.00"))
            pkg.description = description
            pkg.is_active = is_active
            pkg.save()
            messages.success(request, f"Package '{pkg.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect("dashboard:packages")


class DeleteSubscriptionPackageView(StaffRequiredMixin, View):
    def post(self, request, pk):
        pkg = get_object_or_404(SubscriptionPackage, pk=pk)
        if pkg.subscriptions.exists():
            messages.error(request, f"Cannot delete '{pkg.name}' — it has linked subscriptions.")
            return redirect("dashboard:packages")
        name = pkg.name
        pkg.delete()
        messages.success(request, f"Package '{name}' deleted.")
        return redirect("dashboard:packages")


# ---------------------------------------------------------------------------
# Client onboarding
# ---------------------------------------------------------------------------
