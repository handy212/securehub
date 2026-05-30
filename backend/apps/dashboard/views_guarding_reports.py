"""Guarding console: reports."""

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

class GuardingReportsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = (
            FieldReport.objects.select_related("site", "post", "guard", "reviewed_by")
            .prefetch_related("attachments")
            .order_by("-submitted_at")[:200]
        )
        context["attachments"] = FieldReportAttachment.objects.select_related("report", "report__guard", "report__site").order_by("-uploaded_at")[:100]
        context["sites"] = Site.objects.order_by("name")
        context["posts"] = GuardPost.objects.select_related("site").order_by("site__name", "name")
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["report_types"] = FieldReport.ReportType.choices
        context["report_statuses"] = FieldReport.Status.choices
        context["counts"] = self.get_guarding_counts()
        return context

    def post(self, request):
        action = request.POST.get("action", "report")
        try:
            if action == "update_report":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                title = request.POST.get("title", "").strip()
                if not title:
                    raise ValueError("Report title is required.")
                report.site = site
                report.post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                report.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                report.guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                report.report_type = request.POST.get("report_type") or FieldReport.ReportType.OTHER
                next_status = request.POST.get("status") or FieldReport.Status.SUBMITTED
                if next_status in {FieldReport.Status.APPROVED, FieldReport.Status.REJECTED} and next_status != report.status:
                    raise ValueError("Use the review action to approve or reject reports.")
                ensure_report_status_transition(report, next_status)
                report.status = next_status
                report.title = title
                report.body = request.POST.get("body", "").strip()
                report.visible_to_client = not bool(request.POST.get("hidden_from_client"))
                report.submitted_at = (
                    parse_datetime_field(request.POST.get("submitted_at"), label="Submitted time")
                    if request.POST.get("submitted_at")
                    else report.submitted_at
                )
                report.save(
                    update_fields=[
                        "site",
                        "post",
                        "assignment",
                        "guard",
                        "report_type",
                        "status",
                        "title",
                        "body",
                        "visible_to_client",
                        "submitted_at",
                        "updated_at",
                    ]
                )
                messages.success(request, "Field report updated.")
            elif action == "delete_report":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                report.delete()
                messages.success(request, "Field report deleted.")
            elif action == "delete_attachment":
                attachment = get_object_or_404(FieldReportAttachment, pk=request.POST.get("attachment_id"))
                attachment.delete()
                messages.success(request, "Report attachment deleted.")
            elif action == "update_attachment":
                attachment = get_object_or_404(FieldReportAttachment, pk=request.POST.get("attachment_id"))
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                upload = request.FILES.get("file")
                attachment.report = report
                attachment.caption = request.POST.get("caption", "").strip()
                if upload:
                    attachment.file = upload
                    attachment.content_type = getattr(upload, "content_type", "") or attachment.content_type
                attachment.save()
                messages.success(request, "Report attachment updated.")
            elif action == "attachment":
                report = get_object_or_404(FieldReport, pk=request.POST.get("report_id"))
                upload = request.FILES.get("file")
                if not upload:
                    raise ValueError("Attachment file is required.")
                FieldReportAttachment.objects.create(
                    report=report,
                    file=upload,
                    caption=request.POST.get("caption", "").strip(),
                    content_type=getattr(upload, "content_type", "") or "",
                )
                messages.success(request, "Report attachment uploaded.")
            else:
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                FieldReport.objects.create(
                    site=site,
                    post=post,
                    assignment=assignment,
                    guard=guard,
                    report_type=request.POST.get("report_type") or FieldReport.ReportType.OTHER,
                    status=request.POST.get("status")
                    if request.POST.get("status") in {FieldReport.Status.DRAFT, FieldReport.Status.SUBMITTED}
                    else FieldReport.Status.SUBMITTED,
                    title=request.POST.get("title", "").strip(),
                    body=request.POST.get("body", "").strip(),
                    visible_to_client=not bool(request.POST.get("hidden_from_client")),
                    submitted_at=parse_datetime_field(request.POST.get("submitted_at"), label="Submitted time")
                    if request.POST.get("submitted_at")
                    else timezone.now(),
                )
                messages.success(request, "Field report created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-reports")


class GuardingReportReviewView(StaffRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(FieldReport, pk=report_id)
        try:
            review_field_report(
                report,
                actor=request.user,
                status=request.POST.get("status"),
                note=request.POST.get("note", "").strip(),
            )
            messages.success(request, "Report reviewed.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-reports")


class GuardingReportExportView(StaffRequiredMixin, View):
    def get(self, request):
        reports = (
            FieldReport.objects.select_related("site", "post", "guard", "reviewed_by")
            .order_by("-submitted_at")[:1000]
        )
        rows = [
            [
                report.id,
                report.site.name,
                report.post.name if report.post else "",
                report.guard.full_name if report.guard else "",
                report.get_report_type_display(),
                report.get_status_display(),
                report.title,
                report.body,
                report.visible_to_client,
                report.submitted_at,
                report.reviewed_by.username if report.reviewed_by else "",
                report.reviewed_at or "",
                report.review_note,
            ]
            for report in reports
        ]
        return csv_response(
            "guarding-reports.csv",
            [
                "report_id",
                "site",
                "post",
                "guard",
                "type",
                "status",
                "title",
                "body",
                "visible_to_client",
                "submitted_at",
                "reviewed_by",
                "reviewed_at",
                "review_note",
            ],
            rows,
        )


