#!/usr/bin/env python3
"""Split views_guarding.py into domain modules (run from repo root)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "backend/apps/dashboard"
SOURCE = DASH / "views_guarding.py"

GUARDING_IMPORTS = '''\
"""Staff console views for guarding operations."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import Perm
from apps.dashboard.guarding_helpers import (
    apply_credential_from_post,
    attach_guard_compliance_flags,
    populate_guard_profile_from_post,
)
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

'''

HUB = '''\
"""Guarding console views — re-export hub for URLs and tests."""

from apps.dashboard.views_guarding_backoffice import *  # noqa: F403, F401
from apps.dashboard.views_guarding_client import *  # noqa: F403, F401
from apps.dashboard.views_guarding_dispatch import *  # noqa: F403, F401
from apps.dashboard.views_guarding_ops import *  # noqa: F403, F401
from apps.dashboard.views_guarding_reports import *  # noqa: F403, F401

'''

SLICES = (
    ("views_guarding_ops.py", 111, 1267),
    ("views_guarding_reports.py", 1268, 1449),
    ("views_guarding_backoffice.py", 1450, 1827),
    ("views_guarding_client.py", 1828, 1943),
    ("views_guarding_dispatch.py", 1944, None),
)


def extract_lines(path: Path, start: int, end: int | None) -> str:
    lines = path.read_text().splitlines(keepends=True)
    if end is None:
        return "".join(lines[start - 1 :])
    return "".join(lines[start - 1 : end])


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing {SOURCE}")

    text = SOURCE.read_text()
    if text.lstrip().startswith('"""Guarding console views — re-export hub'):
        print("views_guarding.py already a hub; nothing to do.")
        return

    shared_imports = GUARDING_IMPORTS[GUARDING_IMPORTS.find("from __future__") :]
    for filename, start, end in SLICES:
        body = extract_lines(SOURCE, start, end)
        label = filename.removeprefix("views_guarding_").removesuffix(".py")
        doc = f'"""Guarding console: {label}."""\n\n'
        (DASH / filename).write_text(doc + shared_imports + body)
        print(f"Wrote {filename}")

    SOURCE.write_text(HUB)
    print("Replaced views_guarding.py with re-export hub")


if __name__ == "__main__":
    main()
