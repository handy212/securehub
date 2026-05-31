"""Guarding console: client."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
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

class GuardingClientPortalView(GuardingClientRequiredMixin, TemplateView):
    template_name = "dashboard/guarding/client.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access_records = list(ClientPortalAccess.objects.select_related("site").filter(user=self.request.user))
        site_ids = [access.site_id for access in access_records]
        report_site_ids = [access.site_id for access in access_records if access.can_view_reports]
        acknowledge_site_ids = [access.site_id for access in access_records if access.can_acknowledge_reports]
        patrol_site_ids = [access.site_id for access in access_records if access.can_view_patrols]
        attendance_site_ids = [access.site_id for access in access_records if access.can_view_attendance]
        guard_site_ids = [access.site_id for access in access_records if access.can_view_guards]
        today = timezone.localdate()
        guard_window_end = today + timedelta(days=7)
        reports = (
            FieldReport.objects.select_related("site", "post", "guard")
            .prefetch_related("client_acknowledgements")
            .filter(
                site_id__in=report_site_ids,
                visible_to_client=True,
                status=FieldReport.Status.APPROVED,
            )
            .order_by("-submitted_at")[:100]
        )
        patrol_rounds = (
            PatrolRound.objects.select_related(
                "route",
                "route__post",
                "route__post__site",
                "assignment",
                "assignment__guard",
            )
            .prefetch_related("scans")
            .filter(route__post__site_id__in=patrol_site_ids)
            .order_by("-scheduled_start")[:100]
        )
        assignments = (
            ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
            .filter(shift__post__site_id__in=attendance_site_ids)
            .order_by("-shift__starts_at")[:100]
        )
        known_guard_assignments = list(
            ShiftAssignment.objects.select_related("guard", "shift", "shift__post", "shift__post__site")
            .prefetch_related(
                Prefetch(
                    "guard__credentials",
                    queryset=GuardCredential.objects.filter(verified=True).order_by("credential_type", "name"),
                    to_attr="verified_client_credentials",
                )
            )
            .filter(
                shift__post__site_id__in=guard_site_ids,
                shift__starts_at__date__gte=today,
                shift__starts_at__date__lte=guard_window_end,
                status__in=[
                    ShiftAssignment.Status.ASSIGNED,
                    ShiftAssignment.Status.ACCEPTED,
                    ShiftAssignment.Status.CLOCKED_IN,
                ],
            )
            .order_by("shift__starts_at", "shift__post__site__name", "shift__post__name", "guard__last_name")[:100]
        )
        timesheets = (
            GuardTimesheet.objects.select_related("guard", "site", "post")
            .filter(
                site_id__in=attendance_site_ids,
                status__in=[
                    GuardTimesheet.Status.SUBMITTED,
                    GuardTimesheet.Status.APPROVED,
                    GuardTimesheet.Status.EXPORTED,
                ],
            )
            .order_by("-period_start")[:100]
        )
        context.update(
            {
                "access_records": access_records,
                "sites": Site.objects.filter(id__in=site_ids).order_by("name"),
                "reports": reports,
                "patrol_rounds": patrol_rounds,
                "assignments": assignments,
                "known_guard_assignments": known_guard_assignments,
                "timesheets": timesheets,
                "can_export_reports": bool(report_site_ids),
                "acknowledge_site_ids": acknowledge_site_ids,
                "client_counts": {
                    "sites": len(site_ids),
                    "reports": reports.count(),
                    "patrols": patrol_rounds.count(),
                    "assignments": assignments.count(),
                    "guards": len({assignment.guard_id for assignment in known_guard_assignments}),
                },
            }
        )
        return context


class GuardingClientReportAcknowledgeView(GuardingClientRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(FieldReport, pk=report_id)
        try:
            acknowledge_field_report(report, user=request.user, comment=request.POST.get("comment", "").strip())
            messages.success(request, "Report acknowledged.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:client-guarding")


class GuardingClientReportExportView(GuardingClientRequiredMixin, View):
    def get(self, request):
        report_site_ids = ClientPortalAccess.objects.filter(
            user=request.user,
            can_view_reports=True,
        ).values_list("site_id", flat=True)
        reports = (
            FieldReport.objects.select_related("site", "post", "guard")
            .filter(
                site_id__in=report_site_ids,
                visible_to_client=True,
                status=FieldReport.Status.APPROVED,
            )
            .order_by("-submitted_at")[:1000]
        )
        rows = [
            [
                report.site.name,
                report.post.name if report.post else "",
                report.guard.full_name if report.guard else "",
                report.get_report_type_display(),
                report.title,
                report.body,
                report.submitted_at,
            ]
            for report in reports
        ]
        return csv_response(
            "guarding-client-reports.csv",
            ["site", "post", "guard", "type", "title", "body", "submitted_at"],
            rows,
        )

