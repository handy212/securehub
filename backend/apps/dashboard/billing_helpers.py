"""Billing validation helpers for the staff console."""

from __future__ import annotations

from apps.sites.models import Subscription, SubscriptionPayment


def validate_subscription_payment_window(subscription, *, period_start, period_end, exclude_payment_id=None):
    overlapping_payments = subscription.payments.filter(
        period_start__lte=period_end,
        period_end__gte=period_start,
    )
    if exclude_payment_id is not None:
        overlapping_payments = overlapping_payments.exclude(pk=exclude_payment_id)

    if overlapping_payments.exists():
        raise ValueError("Payment periods cannot overlap existing records for this site.")


def validate_reactivation_due_date(subscription, due_date):
    next_status = Subscription.classify_status(
        next_due_date=due_date,
        grace_period_days=subscription.grace_period_days,
    )
    if next_status != Subscription.STATUS_ACTIVE:
        raise ValueError("Reactivation requires a next due date that is today or in the future.")


def billing_day_from_due_date(due_date):
    return min(due_date.day, 28)


def parse_payment_method(raw_value):
    value = str(raw_value or "").strip()
    if not value:
        return ""
    valid_methods = {choice[0] for choice in SubscriptionPayment.METHOD_CHOICES}
    if value not in valid_methods:
        raise ValueError("Please choose a valid payment method.")
    return value
