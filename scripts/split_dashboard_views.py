#!/usr/bin/env python3
"""Split apps/dashboard/views.py into domain modules (run once from repo root)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "backend/apps/dashboard/views.py"
DASH = ROOT / "backend/apps/dashboard"

GUARDING_IMPORTS = '''\
"""Staff console views for guarding operations."""

from __future__ import annotations

import csv
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.views.generic import TemplateView, View

from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import Perm
from apps.dashboard.mixins import GuardingClientRequiredMixin, GuardingOverviewMixin
from apps.dashboard.parsers import (
    csv_response,
    guarding_redirect,
    parse_date_field,
    parse_datetime_field,
    parse_int_field,
    parse_optional_date_field,
    parse_time_field,
)
from apps.dashboard.permissions import StaffRequiredMixin
from apps.guarding.applicant_forms import (
    populate_applicant_from_request,
    populate_applicant_profile_from_request,
)
from apps.guarding.models import (
    Checkpoint,
    CheckpointScan,
    ClientPortalAccess,
    ClockEvent,
    DispatchTask,
    FieldReport,
    FieldReportAcknowledgement,
    FieldReportAttachment,
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantEducation,
    GuardApplicantEmployment,
    GuardApplicantProfile,
    GuardApplicantReference,
    GuardAvailability,
    GuardContract,
    GuardCredential,
    GuardDocument,
    GuardEquipmentIssue,
    GuardInvoice,
    GuardInvoiceLine,
    GuardOffboardingChecklist,
    GuardTimesheet,
    GuardTrainingRecord,
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    LeaveRequest,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    PostOrder,
    ReportTemplate,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    ShiftTemplate,
    WelfareCheck,
)
from apps.guarding.services import (
    acknowledge_field_report,
    acknowledge_panic_alert,
    apply_credential_verification,
    complete_patrol_round,
    count_non_compliant_active_guards,
    ensure_applicant_status_transition,
    ensure_guard_compliance_ready,
    ensure_guard_status_transition,
    ensure_panic_alert_status_transition,
    ensure_report_status_transition,
    ensure_shift_status_transition,
    generate_guard_invoice,
    guard_compliance_issues,
    hire_applicant,
    record_clock_event,
    resolve_panic_alert,
    review_field_report,
    review_leave_request,
    review_shift_swap_request,
    review_timesheet,
    transition_assignment,
    transition_dispatch_task,
    transition_guard_invoice,
    transition_panic_alert,
    transition_patrol_round,
    transition_shift,
)
from apps.sites.models import Site

# Legacy aliases used inside extracted guarding body
_guarding_redirect = guarding_redirect
_parse_datetime_field = parse_datetime_field
_parse_date_field = parse_date_field
_parse_optional_date_field = parse_optional_date_field
_parse_time_field = parse_time_field
_csv_response = csv_response

'''

BILLING_IMPORTS = '''\
"""Staff console views for subscriptions and billing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, View

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
from apps.emergency.models import SiteEmergencyService
from apps.sites.models import Site, Subscription, SubscriptionPackage, SubscriptionPayment

_parse_decimal_field = parse_decimal_field
_parse_int_field = parse_int_field
_parse_date_field = parse_date_field

'''

EMERGENCY_IMPORTS = '''\
"""Staff console views for emergency service add-on management."""

from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, View

from apps.dashboard.parsers import parse_date_field, parse_decimal_field
from apps.dashboard.permissions import StaffRequiredMixin
from apps.emergency.models import (
    AccountEmergencyService,
    EmergencyServicePlan,
    EmergencyServiceStatus,
    SiteEmergencyService,
)
from apps.sites.models import Site

_parse_decimal_field = parse_decimal_field
_parse_date_field = parse_date_field

'''


def extract_lines(path: Path, start: int, end: int) -> str:
    lines = path.read_text().splitlines(keepends=True)
    return "".join(lines[start - 1 : end])


def main() -> None:
    text = VIEWS.read_text()
    lines = text.splitlines(keepends=True)

    # Already split?
    if (DASH / "views_guarding.py").exists() and "AUTO-SPLIT" not in text:
        print("views_guarding.py exists; skipping split (delete it to re-run).")
        return

    guarding_body = extract_lines(VIEWS, 857, 3023)
    billing_body = extract_lines(VIEWS, 4120, 4679)
    emergency_body = extract_lines(VIEWS, 3025, 3203)

    (DASH / "views_guarding.py").write_text(GUARDING_IMPORTS + guarding_body)
    (DASH / "views_billing.py").write_text(BILLING_IMPORTS + billing_body)
    (DASH / "views_emergency.py").write_text(EMERGENCY_IMPORTS + emergency_body)

    print("Wrote views_guarding.py, views_billing.py, views_emergency.py")
    print("Next: create site_helpers.py, parsers.py, mixins.py, billing_helpers.py and trim views.py")


if __name__ == "__main__":
    main()
