"""Guarding console: backoffice."""

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

class GuardingBackOfficeView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/backoffice.html"
    _BACKOFFICE_ACTION_TABS = {
        "contract": "contracts",
        "update_contract": "contracts",
        "delete_contract": "contracts",
        "availability": "attendance",
        "update_availability": "attendance",
        "delete_availability": "attendance",
        "leave": "attendance",
        "update_leave": "attendance",
        "review_leave": "attendance",
        "delete_leave": "attendance",
        "review_shift_swap": "attendance",
        "delete_shift_swap": "attendance",
        "review_timesheet": "attendance",
        "generate_invoice": "attendance",
        "transition_invoice": "attendance",
        "shift_template": "templates",
        "report_template": "templates",
        "client_access": "templates",
        "training": "people",
        "update_training": "people",
        "delete_training": "people",
        "equipment": "people",
        "update_equipment": "people",
        "delete_equipment": "people",
        "offboarding": "people",
        "update_offboarding": "people",
        "delete_offboarding": "people",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contracts"] = GuardContract.objects.select_related("site", "post").order_by("site__name", "name")[:150]
        context["availability_records"] = GuardAvailability.objects.select_related("guard").order_by("-starts_at")[:150]
        context["leave_requests"] = LeaveRequest.objects.select_related("guard", "reviewed_by").order_by("-starts_at")[:150]
        context["shift_swaps"] = ShiftSwapRequest.objects.select_related("assignment", "assignment__shift", "assignment__shift__post", "requested_by", "target_guard", "reviewed_by").order_by("-created_at")[:150]
        context["timesheets"] = GuardTimesheet.objects.select_related("guard", "site", "post", "assignment").order_by("-period_start")[:150]
        context["invoices"] = GuardInvoice.objects.select_related("site", "contract", "generated_by").order_by("-period_start", "-created_at")[:100]
        context["shift_templates"] = ShiftTemplate.objects.select_related("post", "post__site").order_by("post__site__name", "post__name", "name")[:150]
        context["report_templates"] = ReportTemplate.objects.select_related("site").order_by("report_type", "name")[:150]
        context["client_access"] = ClientPortalAccess.objects.select_related("user", "site").order_by("site__name", "user__username")[:150]
        context["training_records"] = GuardTrainingRecord.objects.select_related("guard").order_by("expires_on", "name")[:150]
        context["equipment_issues"] = GuardEquipmentIssue.objects.select_related("guard", "issued_by").order_by("-issued_at")[:150]
        context["offboarding_checklists"] = GuardOffboardingChecklist.objects.select_related("guard", "completed_by").order_by("-created_at")[:150]
        context["sites"] = Site.objects.order_by("name")
        context["posts"] = GuardPost.objects.select_related("site").order_by("site__name", "name")
        context["guards"] = GuardProfile.objects.order_by("last_name", "first_name")
        context["users"] = User.objects.filter(is_staff=False, is_superuser=False).order_by("username")
        context["assignments"] = ShiftAssignment.objects.select_related("guard", "shift", "shift__post").order_by("-shift__starts_at")[:200]
        context["contract_statuses"] = GuardContract.Status.choices
        context["availability_types"] = GuardAvailability.AvailabilityType.choices
        context["leave_statuses"] = LeaveRequest.Status.choices
        context["swap_statuses"] = ShiftSwapRequest.Status.choices
        context["timesheet_statuses"] = GuardTimesheet.Status.choices
        context["invoice_statuses"] = GuardInvoice.Status.choices
        context["report_types"] = FieldReport.ReportType.choices
        context["client_roles"] = ClientPortalAccess.Role.choices
        context["training_statuses"] = GuardTrainingRecord.Status.choices
        context["equipment_statuses"] = GuardEquipmentIssue.Status.choices
        context["counts"] = self.get_guarding_counts()
        pending_leave = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()
        pending_swaps = ShiftSwapRequest.objects.filter(status=ShiftSwapRequest.Status.PENDING).count()
        pending_timesheets = GuardTimesheet.objects.filter(status=GuardTimesheet.Status.SUBMITTED).count()
        context["backoffice_tab_counts"] = {
            "contracts": GuardContract.objects.count(),
            "pending_leave": pending_leave,
            "pending_swaps": pending_swaps,
            "pending_timesheets": pending_timesheets,
            "attendance_actions": pending_leave + pending_swaps + pending_timesheets,
            "shift_templates": ShiftTemplate.objects.filter(is_active=True).count(),
            "report_templates": ReportTemplate.objects.filter(is_active=True).count(),
            "client_access": ClientPortalAccess.objects.count(),
            "open_offboarding": GuardOffboardingChecklist.objects.exclude(
                equipment_returned=True,
                documents_archived=True,
                access_revoked=True,
                final_timesheet_approved=True,
            ).count(),
        }
        return context

    def post(self, request):
        action = request.POST.get("action", "")
        try:
            if action in {"contract", "update_contract"}:
                contract = (
                    get_object_or_404(GuardContract, pk=request.POST.get("contract_id"))
                    if action == "update_contract"
                    else GuardContract()
                )
                contract.site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                contract.post = GuardPost.objects.filter(pk=request.POST.get("post_id")).first()
                contract.name = request.POST.get("name", "").strip()
                if not contract.name:
                    raise ValueError("Contract name is required.")
                contract.status = request.POST.get("status") or GuardContract.Status.DRAFT
                contract.starts_on = parse_date_field(request.POST.get("starts_on"), label="Start date")
                contract.ends_on = parse_date_field(request.POST.get("ends_on"), label="End date") if request.POST.get("ends_on") else None
                contract.bill_rate = parse_decimal_field(request.POST.get("bill_rate", "0"), label="Bill rate", min_value=Decimal("0.00"))
                contract.pay_rate = parse_decimal_field(request.POST.get("pay_rate", "0"), label="Pay rate", min_value=Decimal("0.00"))
                contract.overtime_multiplier = parse_decimal_field(
                    request.POST.get("overtime_multiplier", "1.5"),
                    label="Overtime multiplier",
                    min_value=Decimal("1.00"),
                )
                contract.sla_minutes = parse_int_field(request.POST.get("sla_minutes", "30"), label="SLA minutes", min_value=1)
                contract.notes = request.POST.get("notes", "").strip()
                contract.full_clean()
                contract.save()
                messages.success(request, "Contract saved.")
            elif action == "delete_contract":
                get_object_or_404(GuardContract, pk=request.POST.get("contract_id")).delete()
                messages.success(request, "Contract deleted.")
            elif action in {"availability", "update_availability"}:
                availability = (
                    get_object_or_404(GuardAvailability, pk=request.POST.get("availability_id"))
                    if action == "update_availability"
                    else GuardAvailability(created_by=request.user)
                )
                availability.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                availability.availability_type = request.POST.get("availability_type") or GuardAvailability.AvailabilityType.UNAVAILABLE
                availability.starts_at = parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                availability.ends_at = parse_datetime_field(request.POST.get("ends_at"), label="End time")
                availability.reason = request.POST.get("reason", "").strip()
                availability.full_clean()
                availability.save()
                messages.success(request, "Availability saved.")
            elif action == "delete_availability":
                get_object_or_404(GuardAvailability, pk=request.POST.get("availability_id")).delete()
                messages.success(request, "Availability deleted.")
            elif action in {"leave", "update_leave"}:
                leave = get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id")) if action == "update_leave" else LeaveRequest()
                leave.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                leave.starts_at = parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                leave.ends_at = parse_datetime_field(request.POST.get("ends_at"), label="End time")
                leave.reason = request.POST.get("reason", "").strip()
                if request.POST.get("status"):
                    leave.status = request.POST.get("status")
                leave.full_clean()
                leave.save()
                messages.success(request, "Leave request saved.")
            elif action == "review_leave":
                leave = get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id"))
                review_leave_request(
                    leave,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Leave request reviewed.")
            elif action == "delete_leave":
                get_object_or_404(LeaveRequest, pk=request.POST.get("leave_id")).delete()
                messages.success(request, "Leave request deleted.")
            elif action == "review_shift_swap":
                swap = get_object_or_404(ShiftSwapRequest, pk=request.POST.get("swap_id"))
                review_shift_swap_request(
                    swap,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Shift swap reviewed.")
            elif action == "delete_shift_swap":
                get_object_or_404(ShiftSwapRequest, pk=request.POST.get("swap_id")).delete()
                messages.success(request, "Shift swap deleted.")
            elif action == "review_timesheet":
                timesheet = get_object_or_404(GuardTimesheet, pk=request.POST.get("timesheet_id"))
                review_timesheet(
                    timesheet,
                    actor=request.user,
                    status=request.POST.get("status"),
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Timesheet updated.")
            elif action == "delete_timesheet":
                get_object_or_404(GuardTimesheet, pk=request.POST.get("timesheet_id")).delete()
                messages.success(request, "Timesheet deleted.")
            elif action == "generate_invoice":
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                contract = GuardContract.objects.filter(pk=request.POST.get("contract_id"), site=site).first()
                invoice = generate_guard_invoice(
                    site=site,
                    contract=contract,
                    period_start=parse_date_field(request.POST.get("period_start"), label="Period start"),
                    period_end=parse_date_field(request.POST.get("period_end"), label="Period end"),
                    actor=request.user,
                )
                messages.success(request, f"Invoice {invoice.invoice_number} generated.")
            elif action == "transition_invoice":
                invoice = get_object_or_404(GuardInvoice, pk=request.POST.get("invoice_id"))
                transition_guard_invoice(invoice, status=request.POST.get("status"), actor=request.user)
                messages.success(request, "Invoice updated.")
            elif action == "delete_invoice":
                get_object_or_404(GuardInvoice, pk=request.POST.get("invoice_id")).delete()
                messages.success(request, "Invoice deleted.")
            elif action in {"shift_template", "update_shift_template"}:
                shift_template = (
                    get_object_or_404(ShiftTemplate, pk=request.POST.get("shift_template_id"))
                    if action == "update_shift_template"
                    else ShiftTemplate()
                )
                shift_template.post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                shift_template.name = request.POST.get("name", "").strip()
                if not shift_template.name:
                    raise ValueError("Shift template name is required.")
                shift_template.start_time = parse_time_field(request.POST.get("start_time"), label="Start time")
                shift_template.end_time = parse_time_field(request.POST.get("end_time"), label="End time")
                shift_template.required_guards = parse_int_field(request.POST.get("required_guards", "1"), label="Required guards", min_value=1)
                shift_template.days_of_week = [day for day in request.POST.getlist("days_of_week") if day]
                shift_template.is_active = bool(request.POST.get("is_active"))
                shift_template.notes = request.POST.get("notes", "").strip()
                shift_template.full_clean()
                shift_template.save()
                messages.success(request, "Shift template saved.")
            elif action == "delete_shift_template":
                get_object_or_404(ShiftTemplate, pk=request.POST.get("shift_template_id")).delete()
                messages.success(request, "Shift template deleted.")
            elif action in {"report_template", "update_report_template"}:
                template = (
                    get_object_or_404(ReportTemplate, pk=request.POST.get("template_id"))
                    if action == "update_report_template"
                    else ReportTemplate(created_by=request.user)
                )
                template.name = request.POST.get("name", "").strip()
                if not template.name:
                    raise ValueError("Template name is required.")
                template.report_type = request.POST.get("report_type") or FieldReport.ReportType.OTHER
                template.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                template.is_active = bool(request.POST.get("is_active"))
                template.schema = {"fields": [field.strip() for field in request.POST.get("fields", "").splitlines() if field.strip()]}
                template.save()
                messages.success(request, "Report template saved.")
            elif action == "delete_report_template":
                get_object_or_404(ReportTemplate, pk=request.POST.get("template_id")).delete()
                messages.success(request, "Report template deleted.")
            elif action in {"client_access", "update_client_access"}:
                access = (
                    get_object_or_404(ClientPortalAccess, pk=request.POST.get("access_id"))
                    if action == "update_client_access"
                    else ClientPortalAccess()
                )
                access.user = get_object_or_404(User, pk=request.POST.get("user_id"))
                if access.user.is_staff or access.user.is_superuser:
                    raise ValueError("Operator accounts cannot be assigned guarding client portal access.")
                access.site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                access.role = request.POST.get("role") or ClientPortalAccess.Role.VIEWER
                access.can_view_reports = bool(request.POST.get("can_view_reports"))
                access.can_view_patrols = bool(request.POST.get("can_view_patrols"))
                access.can_view_attendance = bool(request.POST.get("can_view_attendance"))
                access.can_view_guards = bool(request.POST.get("can_view_guards"))
                access.can_acknowledge_reports = bool(request.POST.get("can_acknowledge_reports"))
                access.full_clean()
                access.save()
                messages.success(request, "Client access saved.")
            elif action == "delete_client_access":
                get_object_or_404(ClientPortalAccess, pk=request.POST.get("access_id")).delete()
                messages.success(request, "Client access deleted.")
            elif action in {"training", "update_training"}:
                training = (
                    get_object_or_404(GuardTrainingRecord, pk=request.POST.get("training_id"))
                    if action == "update_training"
                    else GuardTrainingRecord()
                )
                training.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                training.name = request.POST.get("name", "").strip()
                if not training.name:
                    raise ValueError("Training name is required.")
                training.provider = request.POST.get("provider", "").strip()
                training.status = request.POST.get("status") or GuardTrainingRecord.Status.PLANNED
                training.completed_on = parse_date_field(request.POST.get("completed_on"), label="Completed date") if request.POST.get("completed_on") else None
                training.expires_on = parse_date_field(request.POST.get("expires_on"), label="Expiry date") if request.POST.get("expires_on") else None
                training.certificate_number = request.POST.get("certificate_number", "").strip()
                training.notes = request.POST.get("notes", "").strip()
                training.save()
                messages.success(request, "Training record saved.")
            elif action == "delete_training":
                get_object_or_404(GuardTrainingRecord, pk=request.POST.get("training_id")).delete()
                messages.success(request, "Training record deleted.")
            elif action in {"equipment", "update_equipment"}:
                equipment = (
                    get_object_or_404(GuardEquipmentIssue, pk=request.POST.get("equipment_id"))
                    if action == "update_equipment"
                    else GuardEquipmentIssue(issued_by=request.user)
                )
                equipment.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                equipment.item_name = request.POST.get("item_name", "").strip()
                if not equipment.item_name:
                    raise ValueError("Equipment item name is required.")
                equipment.item_code = request.POST.get("item_code", "").strip()
                equipment.quantity = parse_int_field(request.POST.get("quantity", "1"), label="Quantity", min_value=1)
                equipment.status = request.POST.get("status") or GuardEquipmentIssue.Status.ISSUED
                equipment.issued_at = parse_datetime_field(request.POST.get("issued_at"), label="Issued time") if request.POST.get("issued_at") else equipment.issued_at
                equipment.returned_at = parse_datetime_field(request.POST.get("returned_at"), label="Returned time") if request.POST.get("returned_at") else None
                equipment.notes = request.POST.get("notes", "").strip()
                equipment.save()
                from apps.guarding.asset_services import sync_offboarding_equipment_flag

                sync_offboarding_equipment_flag(equipment.guard)
                messages.success(request, "Equipment issue saved.")
            elif action == "delete_equipment":
                get_object_or_404(GuardEquipmentIssue, pk=request.POST.get("equipment_id")).delete()
                messages.success(request, "Equipment issue deleted.")
            elif action in {"offboarding", "update_offboarding"}:
                checklist = (
                    get_object_or_404(GuardOffboardingChecklist, pk=request.POST.get("offboarding_id"))
                    if action == "update_offboarding"
                    else GuardOffboardingChecklist()
                )
                checklist.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                checklist.equipment_returned = bool(request.POST.get("equipment_returned"))
                checklist.documents_archived = bool(request.POST.get("documents_archived"))
                checklist.access_revoked = bool(request.POST.get("access_revoked"))
                checklist.final_timesheet_approved = bool(request.POST.get("final_timesheet_approved"))
                checklist.exit_notes = request.POST.get("exit_notes", "").strip()
                if checklist.is_complete and checklist.completed_at is None:
                    checklist.completed_by = request.user
                    checklist.completed_at = timezone.now()
                checklist.save()
                messages.success(request, "Offboarding checklist saved.")
            elif action == "delete_offboarding":
                get_object_or_404(GuardOffboardingChecklist, pk=request.POST.get("offboarding_id")).delete()
                messages.success(request, "Offboarding checklist deleted.")
        except Exception as exc:
            messages.error(request, str(exc))
        tab = self._BACKOFFICE_ACTION_TABS.get(action)
        if tab:
            return redirect(f"{reverse('dashboard:guarding-backoffice')}?tab={tab}")
        return redirect("dashboard:guarding-backoffice")


class GuardingTimesheetExportView(StaffRequiredMixin, View):
    def get(self, request):
        timesheets = (
            GuardTimesheet.objects.select_related("guard", "site", "post", "assignment")
            .order_by("-period_start")[:1000]
        )
        rows = [
            [
                sheet.id,
                sheet.guard.full_name,
                sheet.site.name,
                sheet.post.name if sheet.post else "",
                sheet.period_start,
                sheet.period_end,
                sheet.regular_minutes,
                sheet.overtime_minutes,
                sheet.total_minutes,
                sheet.pay_amount,
                sheet.bill_amount,
                sheet.get_status_display(),
                sheet.approved_by.username if sheet.approved_by else "",
                sheet.approved_at or "",
                sheet.export_reference,
            ]
            for sheet in timesheets
        ]
        return csv_response(
            "guarding-timesheets.csv",
            [
                "timesheet_id",
                "guard",
                "site",
                "post",
                "period_start",
                "period_end",
                "regular_minutes",
                "overtime_minutes",
                "total_minutes",
                "pay_amount",
                "bill_amount",
                "status",
                "approved_by",
                "approved_at",
                "export_reference",
            ],
            rows,
        )
