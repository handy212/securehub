"""Guarding console: ops."""

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

class GuardingOverviewView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()
        day_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time()),
            timezone.get_current_timezone(),
        )
        day_end = day_start + timedelta(days=1)
        active_dispatch_statuses = [
            DispatchTask.Status.OPEN,
            DispatchTask.Status.ASSIGNED,
            DispatchTask.Status.ACCEPTED,
            DispatchTask.Status.EN_ROUTE,
            DispatchTask.Status.ARRIVED,
        ]
        context["counts"] = self.get_guarding_counts()
        todays_shifts = Shift.objects.filter(starts_at__lt=day_end, ends_at__gte=day_start)
        required_guards_today = todays_shifts.aggregate(total=Sum("required_guards"))["total"] or 0
        assigned_guards_today = ShiftAssignment.objects.filter(shift__in=todays_shifts).exclude(
            status__in=[ShiftAssignment.Status.DECLINED, ShiftAssignment.Status.REMOVED, ShiftAssignment.Status.NO_SHOW]
        ).count()
        context["today_summary"] = {
            "shifts": todays_shifts.count(),
            "required_guards": required_guards_today,
            "assigned_guards": assigned_guards_today,
            "coverage_gap": max(required_guards_today - assigned_guards_today, 0),
            "coverage_percent": min(100, round((assigned_guards_today / required_guards_today) * 100))
            if required_guards_today
            else 0,
            "clocked_in": ShiftAssignment.objects.filter(
                shift__in=todays_shifts,
                status=ShiftAssignment.Status.CLOCKED_IN,
            ).count(),
            "patrol_scans": CheckpointScan.objects.filter(scanned_at__gte=day_start, scanned_at__lt=day_end).count(),
            "reports": FieldReport.objects.filter(submitted_at__gte=day_start, submitted_at__lt=day_end).count(),
        }
        context["open_panic_alerts"] = (
            GuardPanicAlert.objects.select_related("guard", "site")
            .filter(status=GuardPanicAlert.Status.OPEN)
            .order_by("-created_at")[:8]
        )
        context["active_dispatch_tasks"] = (
            DispatchTask.objects.select_related("site", "assigned_guard")
            .filter(status__in=active_dispatch_statuses)
            .order_by("-created_at")[:8]
        )
        context["upcoming_shifts"] = (
            Shift.objects.select_related("post", "post__site")
            .prefetch_related("assignments__guard")
            .filter(ends_at__gte=now)
            .order_by("starts_at")[:8]
        )
        context["welfare_checks"] = (
            WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post")
            .filter(status__in=[WelfareCheck.Status.PENDING, WelfareCheck.Status.ESCALATED])
            .order_by("due_at")[:8]
        )
        context["recent_scans"] = (
            CheckpointScan.objects.select_related("checkpoint", "guard", "patrol_round", "patrol_round__route")
            .order_by("-scanned_at")[:8]
        )
        context["recent_reports"] = (
            FieldReport.objects.select_related("site", "post", "guard")
            .order_by("-submitted_at")[:8]
        )
        context["workflow_events"] = (
            GuardingEventLog.objects.select_related("guard", "site", "actor")
            .order_by("-created_at")[:10]
        )
        context["workflow_event_counts"] = {
            "critical": GuardingEventLog.objects.filter(severity=GuardingEventLog.Severity.CRITICAL).count(),
            "warning": GuardingEventLog.objects.filter(severity=GuardingEventLog.Severity.WARNING).count(),
        }
        expiry_cutoff = today + timedelta(days=30)
        context["backoffice_summary"] = {
            "active_contracts": GuardContract.objects.filter(status=GuardContract.Status.ACTIVE).count(),
            "draft_timesheets": GuardTimesheet.objects.filter(status=GuardTimesheet.Status.DRAFT).count(),
            "pending_timesheets": GuardTimesheet.objects.filter(status=GuardTimesheet.Status.SUBMITTED).count(),
            "expiring_credentials": GuardCredential.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
            "expiring_documents": GuardDocument.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
            "expiring_training": GuardTrainingRecord.objects.filter(expires_on__gte=today, expires_on__lte=expiry_cutoff).count(),
        }
        return context


class GuardingApplicantsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/applicants.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applicants = (
            GuardApplicant.objects.select_related("hired_guard", "created_by", "profile")
            .prefetch_related("documents", "education_records", "employment_records", "references")
            .order_by("-created_at")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            applicants = applicants.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(national_id__icontains=query)
            )
        context["applicants"] = applicants[:200]
        context["statuses"] = GuardApplicant.Status.choices
        context["background_check_statuses"] = [
            ("pending", "Pending"),
            ("clear", "Clear"),
            ("failed", "Failed"),
        ]
        context["gender_choices"] = [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not", "Prefer not to say"),
        ]
        context["marital_status_choices"] = [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
            ("other", "Other"),
        ]
        context["shift_preference_choices"] = GuardApplicantProfile.ShiftPreference.choices
        context["applicant_document_types"] = GuardApplicantDocument.DocumentType.choices
        context["public_apply_url"] = self.request.build_absolute_uri("/apply/guard/")
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["new_applicant"] = GuardApplicant(status=GuardApplicant.Status.APPLIED)
        return context

    def _save_applicant_core(self, applicant, request):
        if not applicant.first_name or not applicant.last_name:
            raise ValueError("First name and last name are required.")
        next_status = request.POST.get("status") or applicant.status or GuardApplicant.Status.APPLIED
        ensure_applicant_status_transition(applicant, next_status)
        applicant.status = next_status
        applicant.save()
        populate_applicant_profile_from_request(applicant, request, parse_dates=parse_date_field)

    def post(self, request):
        action = request.POST.get("action", "applicant")
        parse_date = parse_date_field
        try:
            if action == "update_applicant":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                populate_applicant_from_request(applicant, request, parse_dates=parse_date)
                self._save_applicant_core(applicant, request)
                messages.success(request, "Applicant updated.")
            elif action == "delete_applicant":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                if applicant.hired_guard_id:
                    raise ValueError("Hired applicants are linked to guard profiles and cannot be deleted here.")
                applicant.delete()
                messages.success(request, "Applicant deleted.")
            elif action == "applicant_document":
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                upload = request.FILES.get("file")
                if not upload:
                    raise ValueError("Document file is required.")
                GuardApplicantDocument.objects.create(
                    applicant=applicant,
                    document_type=request.POST.get("document_type") or GuardApplicantDocument.DocumentType.OTHER,
                    title=request.POST.get("title", "").strip() or upload.name,
                    file=upload,
                    reference_number=request.POST.get("reference_number", "").strip(),
                    notes=request.POST.get("notes", "").strip(),
                    uploaded_by=request.user,
                )
                messages.success(request, "Document uploaded.")
            elif action == "delete_applicant_document":
                get_object_or_404(GuardApplicantDocument, pk=request.POST.get("document_id")).delete()
                messages.success(request, "Document deleted.")
            elif action in {"applicant_education", "update_applicant_education"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantEducation, pk=request.POST.get("education_id"))
                    if action == "update_applicant_education"
                    else GuardApplicantEducation(applicant=applicant)
                )
                record.education_level = request.POST.get("education_level", "").strip()
                if not record.education_level:
                    raise ValueError("Education level is required.")
                record.institution_name = request.POST.get("institution_name", "").strip()
                year_raw = request.POST.get("year_completed", "").strip()
                record.year_completed = int(year_raw) if year_raw else None
                record.certificates_obtained = request.POST.get("certificates_obtained", "").strip()
                record.save()
                messages.success(request, "Education record saved.")
            elif action == "delete_applicant_education":
                get_object_or_404(GuardApplicantEducation, pk=request.POST.get("education_id")).delete()
                messages.success(request, "Education record deleted.")
            elif action in {"applicant_employment", "update_applicant_employment"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantEmployment, pk=request.POST.get("employment_id"))
                    if action == "update_applicant_employment"
                    else GuardApplicantEmployment(applicant=applicant)
                )
                record.company_name = request.POST.get("company_name", "").strip()
                if not record.company_name:
                    raise ValueError("Company name is required.")
                record.position = request.POST.get("position", "").strip()
                record.duties = request.POST.get("duties", "").strip()
                record.supervisor_name = request.POST.get("supervisor_name", "").strip()
                record.supervisor_contact = request.POST.get("supervisor_contact", "").strip()
                record.reason_for_leaving = request.POST.get("reason_for_leaving", "").strip()
                years_raw = request.POST.get("years_experience", "").strip()
                record.years_experience = Decimal(years_raw) if years_raw else None
                if request.POST.get("started_on"):
                    record.started_on = parse_date(request.POST.get("started_on"), label="Start date")
                if request.POST.get("ended_on"):
                    record.ended_on = parse_date(request.POST.get("ended_on"), label="End date")
                record.save()
                messages.success(request, "Employment record saved.")
            elif action == "delete_applicant_employment":
                get_object_or_404(GuardApplicantEmployment, pk=request.POST.get("employment_id")).delete()
                messages.success(request, "Employment record deleted.")
            elif action in {"applicant_reference", "update_applicant_reference"}:
                applicant = get_object_or_404(GuardApplicant, pk=request.POST.get("applicant_id"))
                record = (
                    get_object_or_404(GuardApplicantReference, pk=request.POST.get("reference_id"))
                    if action == "update_applicant_reference"
                    else GuardApplicantReference(applicant=applicant)
                )
                record.full_name = request.POST.get("full_name", "").strip()
                if not record.full_name:
                    raise ValueError("Reference name is required.")
                record.company = request.POST.get("company", "").strip()
                record.position = request.POST.get("position", "").strip()
                record.phone_number = request.POST.get("phone_number", "").strip()
                record.save()
                messages.success(request, "Reference saved.")
            elif action == "delete_applicant_reference":
                get_object_or_404(GuardApplicantReference, pk=request.POST.get("reference_id")).delete()
                messages.success(request, "Reference deleted.")
            elif action == "applicant":
                applicant = GuardApplicant(created_by=request.user, status=GuardApplicant.Status.APPLIED)
                populate_applicant_from_request(applicant, request, parse_dates=parse_date)
                self._save_applicant_core(applicant, request)
                messages.success(request, "Applicant created.")
            else:
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-applicants")


class GuardingApplicantHireView(StaffRequiredMixin, View):
    def post(self, request, applicant_id):
        applicant = get_object_or_404(GuardApplicant, pk=applicant_id)
        try:
            guard = hire_applicant(
                applicant,
                employee_number=request.POST.get("employee_number", "").strip(),
                actor=request.user,
            )
            messages.success(request, f"{guard.full_name} hired as {guard.employee_number}.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-applicants")


class GuardingApplicantPdfView(StaffRequiredMixin, View):
    def get(self, request, applicant_id):
        from apps.guarding.reports.pdf import render_guard_applicant_pdf

        applicant = get_object_or_404(GuardApplicant, pk=applicant_id)
        pdf_bytes = render_guard_applicant_pdf(applicant)
        filename = f"guard-application-{applicant.last_name}-{applicant.pk}.pdf".replace(" ", "-")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class GuardingGuardsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/guards.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guards = (
            GuardProfile.objects.select_related("user", "supervisor")
            .prefetch_related("credentials", "documents")
            .order_by("last_name", "first_name")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            guards = guards.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(employee_number__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(email__icontains=query)
                | Q(metadata__national_id__icontains=query)
            )
        guards = list(guards[:200])
        attach_guard_compliance_flags(guards)
        context["guards"] = guards
        context["users"] = User.objects.filter(is_active=True).order_by("username")
        context["supervisors"] = User.objects.filter(is_active=True, is_staff=True).order_by("username")
        context["statuses"] = GuardProfile.Status.choices
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["credential_types"] = GuardCredential.CredentialType.choices
        context["document_types"] = GuardDocument.DocumentType.choices
        from apps.guarding.guard_forms import guard_form_choices

        context.update(guard_form_choices())
        context["credentials"] = (
            GuardCredential.objects.select_related("guard", "verified_by")
            .order_by("expires_on", "name")[:100]
        )
        context["documents"] = GuardDocument.objects.select_related("guard", "uploaded_by").order_by("-created_at")[:100]
        context["location_pings"] = GuardLocationPing.objects.select_related("guard", "assignment").order_by("-created_at")[:100]
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        return context

    def post(self, request):
        action = request.POST.get("action", "guard")
        if action == "update_guard":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                employee_number = request.POST.get("employee_number", "").strip()
                first_name = request.POST.get("first_name", "").strip()
                last_name = request.POST.get("last_name", "").strip()
                if not employee_number or not first_name or not last_name:
                    raise ValueError("Employee number, first name, and last name are required.")
                if GuardProfile.objects.filter(employee_number=employee_number).exclude(pk=guard.pk).exists():
                    raise ValueError("Employee number is already in use.")
                guard.user = User.objects.filter(pk=request.POST.get("user_id")).first()
                guard.supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
                guard.employee_number = employee_number
                guard.first_name = first_name
                guard.last_name = last_name
                populate_guard_profile_from_post(guard, request)
                next_status = request.POST.get("status") or GuardProfile.Status.ACTIVE
                ensure_guard_status_transition(guard, next_status)
                guard.status = next_status
                if guard.status == GuardProfile.Status.TERMINATED and not guard.termination_date:
                    guard.termination_date = timezone.localdate()
                guard.save(
                    update_fields=[
                        "user",
                        "supervisor",
                        "employee_number",
                        "first_name",
                        "last_name",
                        "phone_number",
                        "email",
                        "home_address",
                        "emergency_contact_name",
                        "emergency_contact_phone",
                        "hire_date",
                        "termination_date",
                        "notes",
                        "metadata",
                        "status",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard profile updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_guard":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                guard.delete()
                messages.success(request, "Guard profile deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_credential":
            try:
                credential = get_object_or_404(GuardCredential, pk=request.POST.get("credential_id"))
                credential.delete()
                messages.success(request, "Guard credential deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_credential":
            try:
                credential = get_object_or_404(GuardCredential, pk=request.POST.get("credential_id"))
                credential.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                apply_credential_from_post(credential, request, actor=request.user)
                credential.save(
                    update_fields=[
                        "guard",
                        "credential_type",
                        "name",
                        "issuing_authority",
                        "reference_number",
                        "issued_on",
                        "expires_on",
                        "verified",
                        "verified_by",
                        "verified_at",
                        "notes",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard credential updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_document":
            try:
                document = get_object_or_404(GuardDocument, pk=request.POST.get("document_id"))
                document.delete()
                messages.success(request, "Guard document deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "location_ping":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                GuardLocationPing.objects.create(
                    guard=guard,
                    assignment=ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first(),
                    latitude=parse_decimal_field(request.POST.get("latitude"), label="Latitude"),
                    longitude=parse_decimal_field(request.POST.get("longitude"), label="Longitude"),
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    speed_mps=request.POST.get("speed_mps") or None,
                    heading_deg=request.POST.get("heading_deg") or None,
                    device_timestamp=parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None,
                )
                messages.success(request, "Location ping recorded.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_location_ping":
            try:
                ping = get_object_or_404(GuardLocationPing, pk=request.POST.get("location_ping_id"))
                ping.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                ping.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                ping.latitude = parse_decimal_field(request.POST.get("latitude"), label="Latitude")
                ping.longitude = parse_decimal_field(request.POST.get("longitude"), label="Longitude")
                ping.accuracy_m = request.POST.get("accuracy_m") or None
                ping.speed_mps = request.POST.get("speed_mps") or None
                ping.heading_deg = request.POST.get("heading_deg") or None
                ping.device_timestamp = (
                    parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None
                )
                ping.save()
                messages.success(request, "Location ping updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "delete_location_ping":
            try:
                ping = get_object_or_404(GuardLocationPing, pk=request.POST.get("location_ping_id"))
                ping.delete()
                messages.success(request, "Location ping deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "update_document":
            try:
                document = get_object_or_404(GuardDocument, pk=request.POST.get("document_id"))
                upload = request.FILES.get("file")
                document.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                document.document_type = request.POST.get("document_type") or GuardDocument.DocumentType.OTHER
                document.title = request.POST.get("title", "").strip()
                document.reference_number = request.POST.get("reference_number", "").strip()
                document.expires_on = request.POST.get("expires_on") or None
                document.notes = request.POST.get("notes", "").strip()
                if upload:
                    document.file = upload
                document.save()
                messages.success(request, "Guard document updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "credential":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                credential = GuardCredential(guard=guard)
                apply_credential_from_post(credential, request, actor=request.user)
                credential.save()
                messages.success(request, "Guard credential created.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        if action == "document":
            try:
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                GuardDocument.objects.create(
                    guard=guard,
                    document_type=request.POST.get("document_type") or GuardDocument.DocumentType.OTHER,
                    title=request.POST.get("title", "").strip(),
                    file=request.FILES.get("file"),
                    reference_number=request.POST.get("reference_number", "").strip(),
                    expires_on=request.POST.get("expires_on") or None,
                    notes=request.POST.get("notes", "").strip(),
                    uploaded_by=request.user,
                )
                messages.success(request, "Guard document recorded.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-guards")
        employee_number = request.POST.get("employee_number", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        if not employee_number or not first_name or not last_name:
            messages.error(request, "Employee number, first name, and last name are required.")
            return redirect("dashboard:guarding-guards")
        if GuardProfile.objects.filter(employee_number=employee_number).exists():
            messages.error(request, "Employee number is already in use.")
            return redirect("dashboard:guarding-guards")
        user = User.objects.filter(pk=request.POST.get("user_id")).first()
        supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
        next_status = request.POST.get("status") or GuardProfile.Status.INACTIVE
        guard = GuardProfile(
            user=user,
            employee_number=employee_number,
            first_name=first_name,
            last_name=last_name,
            supervisor=supervisor,
            status=next_status,
            hire_date=timezone.localdate(),
        )
        populate_guard_profile_from_post(guard, request)
        if next_status == GuardProfile.Status.ACTIVE:
            try:
                ensure_guard_compliance_ready(guard)
            except Exception as exc:
                messages.error(request, str(exc))
                return redirect("dashboard:guarding-guards")
        guard.save()
        messages.success(request, "Guard profile created.")
        return redirect("dashboard:guarding-guards")


class GuardingPostsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/posts.html"

    def get_context_data(self, **kwargs):
        from .guarding_asset_console import posts_asset_context

        context = super().get_context_data(**kwargs)
        context.update(posts_asset_context())
        context["all_posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        posts = GuardPost.objects.select_related("site", "supervisor").order_by("site__name", "name")
        query = self.request.GET.get("q", "").strip()
        if query:
            posts = posts.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(site__name__icontains=query))
        context["posts"] = posts[:200]
        context["sites"] = Site.objects.order_by("name")
        context["supervisors"] = User.objects.filter(is_active=True, is_staff=True).order_by("username")
        context["counts"] = self.get_guarding_counts()
        context["current_query"] = query
        context["post_orders"] = PostOrder.objects.select_related("post", "post__site", "created_by").order_by("post__site__name", "post__name", "-created_at")[:200]
        return context

    def post(self, request):
        from .guarding_asset_console import handle_posts_asset_action

        action = request.POST.get("action", "post")
        if handle_posts_asset_action(request):
            return redirect("dashboard:guarding-posts")
        if action == "update_post":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                name = request.POST.get("name", "").strip()
                if not name:
                    raise ValueError("Post name is required.")
                post.site = site
                post.name = name
                post.code = request.POST.get("code", "").strip()
                post.description = request.POST.get("description", "").strip()
                post.geofence_radius_m = parse_int_field(
                    request.POST.get("geofence_radius_m") or 150,
                    label="Geofence radius",
                    min_value=1,
                )
                post.supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
                post.is_active = not bool(request.POST.get("inactive"))
                post.save(
                    update_fields=[
                        "site",
                        "name",
                        "code",
                        "description",
                        "geofence_radius_m",
                        "supervisor",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Guard post updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "delete_post":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                post.delete()
                messages.success(request, "Guard post deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "update_post_order":
            try:
                order = get_object_or_404(PostOrder, pk=request.POST.get("order_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                title = request.POST.get("title", "").strip()
                body = request.POST.get("body", "").strip()
                if not title or not body:
                    raise ValueError("Order title and body are required.")
                order.post = post
                order.title = title
                order.body = body
                order.effective_from = request.POST.get("effective_from") or None
                order.effective_until = request.POST.get("effective_until") or None
                order.is_active = not bool(request.POST.get("inactive"))
                order.save(
                    update_fields=[
                        "post",
                        "title",
                        "body",
                        "effective_from",
                        "effective_until",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Post order updated.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "delete_post_order":
            try:
                order = get_object_or_404(PostOrder, pk=request.POST.get("order_id"))
                order.delete()
                messages.success(request, "Post order deleted.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        if action == "post_order":
            try:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                PostOrder.objects.create(
                    post=post,
                    title=request.POST.get("title", "").strip(),
                    body=request.POST.get("body", "").strip(),
                    effective_from=request.POST.get("effective_from") or None,
                    effective_until=request.POST.get("effective_until") or None,
                    is_active=not bool(request.POST.get("inactive")),
                    created_by=request.user,
                )
                messages.success(request, "Post order created.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:guarding-posts")
        site = get_object_or_404(Site, pk=request.POST.get("site_id"))
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Post name is required.")
            return redirect("dashboard:guarding-posts")
        supervisor = User.objects.filter(pk=request.POST.get("supervisor_id"), is_staff=True).first()
        try:
            GuardPost.objects.create(
                site=site,
                name=name,
                code=request.POST.get("code", "").strip(),
                description=request.POST.get("description", "").strip(),
                geofence_radius_m=parse_int_field(
                    request.POST.get("geofence_radius_m") or 150,
                    label="Geofence radius",
                    min_value=1,
                ),
                supervisor=supervisor,
            )
            messages.success(request, "Guard post created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-posts")


class GuardingShiftsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/shifts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shifts"] = (
            Shift.objects.select_related("post", "post__site")
            .prefetch_related("assignments__guard", "assignments__assigned_by")
            .order_by("-starts_at")[:200]
        )
        context["posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        guards = list(
            GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        )
        attach_guard_compliance_flags(guards)
        context["guards"] = guards
        context["assignments"] = (
            ShiftAssignment.objects.select_related("shift", "shift__post", "guard", "assigned_by")
            .order_by("-shift__starts_at")[:200]
        )
        context["clock_events"] = ClockEvent.objects.select_related("assignment", "assignment__guard", "assignment__shift__post").order_by("-created_at")[:100]
        context["welfare_checks"] = WelfareCheck.objects.select_related("assignment", "assignment__guard", "assignment__shift__post").order_by("due_at")[:100]
        context["statuses"] = Shift.Status.choices
        context["assignment_statuses"] = ShiftAssignment.Status.choices
        context["clock_event_types"] = ClockEvent.EventType.choices
        context["welfare_statuses"] = WelfareCheck.Status.choices
        context["counts"] = self.get_guarding_counts()
        from apps.guarding.asset_models import (
            GuardAssetDepot,
            GuardAssetType,
            GuardAssetUnit,
            ShiftAssetManifest,
            ShiftAssetManifestLine,
        )

        context["asset_types"] = GuardAssetType.objects.filter(is_active=True).order_by("name")
        context["asset_depots"] = GuardAssetDepot.objects.filter(is_active=True).order_by("name")
        context["available_units"] = GuardAssetUnit.objects.filter(
            status=GuardAssetUnit.Status.AVAILABLE,
        ).select_related("asset_type", "depot")[:500]
        context["shift_manifests"] = (
            ShiftAssetManifest.objects.select_related(
                "assignment__guard",
                "assignment__shift__post",
                "assignment__shift__post__site",
            )
            .prefetch_related("lines__asset_type", "lines__asset_unit")
            .order_by("-created_at")[:100]
        )
        context["manifest_statuses"] = ShiftAssetManifest.Status.choices
        context["manifest_line_statuses"] = ShiftAssetManifestLine.Status.choices
        return context

    def post(self, request):
        from .guarding_asset_console import handle_shifts_asset_action

        action = request.POST.get("action", "shift")
        try:
            if handle_shifts_asset_action(request):
                return redirect("dashboard:guarding-shifts")
            if action == "update_shift":
                shift = get_object_or_404(Shift, pk=request.POST.get("shift_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                next_status = request.POST.get("status") or Shift.Status.PUBLISHED
                shift.post = post
                shift.starts_at = parse_datetime_field(request.POST.get("starts_at"), label="Start time")
                shift.ends_at = parse_datetime_field(request.POST.get("ends_at"), label="End time")
                shift.required_guards = parse_int_field(
                    request.POST.get("required_guards") or 1,
                    label="Required guards",
                    min_value=1,
                )
                shift.notes = request.POST.get("notes", "").strip()
                shift.save(
                    update_fields=[
                        "post",
                        "starts_at",
                        "ends_at",
                        "required_guards",
                        "notes",
                        "updated_at",
                    ]
                )
                existing_guard_ids = set(shift.assignments.values_list("guard_id", flat=True))
                for guard_id in request.POST.getlist("guard_ids"):
                    guard = GuardProfile.objects.filter(pk=guard_id, status=GuardProfile.Status.ACTIVE).first()
                    if guard and guard.pk not in existing_guard_ids:
                        ensure_guard_compliance_ready(guard)
                        ShiftAssignment.objects.get_or_create(shift=shift, guard=guard, defaults={"assigned_by": request.user})
                if next_status != shift.status:
                    transition_shift(shift, next_status)
                messages.success(request, "Shift updated.")
            elif action == "delete_shift":
                shift = get_object_or_404(Shift, pk=request.POST.get("shift_id"))
                shift.delete()
                messages.success(request, "Shift deleted.")
            elif action == "update_assignment":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                note = request.POST.get("notes", "").strip()
                transition_assignment(
                    assignment,
                    request.POST.get("status") or ShiftAssignment.Status.ASSIGNED,
                    note=note,
                )
                if note:
                    assignment.notes = note
                    assignment.save(update_fields=["notes", "updated_at"])
                messages.success(request, "Shift assignment updated.")
            elif action == "delete_assignment":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                assignment.delete()
                messages.success(request, "Shift assignment deleted.")
            elif action == "delete_clock_event":
                event = get_object_or_404(ClockEvent, pk=request.POST.get("clock_event_id"))
                event.delete()
                messages.success(request, "Clock event deleted.")
            elif action == "update_clock_event":
                event = get_object_or_404(ClockEvent, pk=request.POST.get("clock_event_id"))
                event.assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                event.event_type = request.POST.get("event_type") or ClockEvent.EventType.CLOCK_IN
                event.latitude = request.POST.get("latitude") or None
                event.longitude = request.POST.get("longitude") or None
                event.accuracy_m = request.POST.get("accuracy_m") or None
                event.within_geofence = bool(request.POST.get("within_geofence"))
                event.device_timestamp = (
                    parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None
                )
                event.save()
                messages.success(request, "Clock event updated.")
            elif action == "update_welfare_check":
                check = get_object_or_404(WelfareCheck, pk=request.POST.get("welfare_check_id"))
                check.due_at = parse_datetime_field(request.POST.get("due_at"), label="Due time")
                check.status = request.POST.get("status") or WelfareCheck.Status.PENDING
                check.response_note = request.POST.get("response_note", "").strip()
                if check.status == WelfareCheck.Status.CONFIRMED and check.responded_at is None:
                    check.responded_at = timezone.now()
                check.save(update_fields=["due_at", "status", "response_note", "responded_at", "updated_at"])
                messages.success(request, "Welfare check updated.")
            elif action == "delete_welfare_check":
                check = get_object_or_404(WelfareCheck, pk=request.POST.get("welfare_check_id"))
                check.delete()
                messages.success(request, "Welfare check deleted.")
            elif action == "clock_event":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                record_clock_event(
                    assignment=assignment,
                    event_type=request.POST.get("event_type") or ClockEvent.EventType.CLOCK_IN,
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    within_geofence=bool(request.POST.get("within_geofence")),
                    device_timestamp=parse_datetime_field(request.POST.get("device_timestamp"), label="Device timestamp")
                    if request.POST.get("device_timestamp")
                    else None,
                )
                messages.success(request, "Clock event recorded.")
            elif action == "welfare_check":
                assignment = get_object_or_404(ShiftAssignment, pk=request.POST.get("assignment_id"))
                WelfareCheck.objects.create(
                    assignment=assignment,
                    due_at=parse_datetime_field(request.POST.get("due_at"), label="Due time"),
                    status=request.POST.get("status") or WelfareCheck.Status.PENDING,
                    response_note=request.POST.get("response_note", "").strip(),
                )
                messages.success(request, "Welfare check created.")
            else:
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                shift = Shift.objects.create(
                    post=post,
                    starts_at=parse_datetime_field(request.POST.get("starts_at"), label="Start time"),
                    ends_at=parse_datetime_field(request.POST.get("ends_at"), label="End time"),
                    status=request.POST.get("status") or Shift.Status.PUBLISHED,
                    required_guards=parse_int_field(request.POST.get("required_guards") or 1, label="Required guards", min_value=1),
                    notes=request.POST.get("notes", "").strip(),
                    created_by=request.user,
                )
                for guard_id in request.POST.getlist("guard_ids"):
                    guard = GuardProfile.objects.filter(pk=guard_id, status=GuardProfile.Status.ACTIVE).first()
                    if guard:
                        ensure_guard_compliance_ready(guard)
                        ShiftAssignment.objects.get_or_create(shift=shift, guard=guard, defaults={"assigned_by": request.user})
                messages.success(request, "Shift created.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-shifts")


class GuardingPatrolsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/patrols.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["checkpoints"] = Checkpoint.objects.select_related("post", "post__site").order_by("post__site__name", "post__name", "name")[:200]
        context["routes"] = PatrolRoute.objects.select_related("post", "post__site").prefetch_related("patrolroutecheckpoint_set__checkpoint").order_by("post__site__name", "name")[:200]
        context["rounds"] = PatrolRound.objects.select_related("route", "assignment", "assignment__guard").prefetch_related("scans").order_by("-scheduled_start")[:200]
        context["scans"] = CheckpointScan.objects.select_related("patrol_round", "checkpoint", "guard").order_by("-scanned_at")[:100]
        context["posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["counts"] = self.get_guarding_counts()
        return context

    def post(self, request):
        action = request.POST.get("action")
        try:
            if action == "update_checkpoint":
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                name = request.POST.get("name", "").strip()
                code = request.POST.get("code", "").strip()
                if not name or not code:
                    raise ValueError("Checkpoint name and code are required.")
                checkpoint.post = post
                checkpoint.name = name
                checkpoint.code = code
                checkpoint.checkpoint_type = request.POST.get("checkpoint_type") or Checkpoint.CheckpointType.QR
                checkpoint.geofence_radius_m = parse_int_field(
                    request.POST.get("geofence_radius_m") or 50,
                    label="Geofence radius",
                    min_value=1,
                )
                checkpoint.is_active = not bool(request.POST.get("inactive"))
                checkpoint.save(
                    update_fields=[
                        "post",
                        "name",
                        "code",
                        "checkpoint_type",
                        "geofence_radius_m",
                        "is_active",
                        "updated_at",
                    ]
                )
                messages.success(request, "Checkpoint updated.")
            elif action == "delete_checkpoint":
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                checkpoint.delete()
                messages.success(request, "Checkpoint deleted.")
            elif action == "update_route":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                name = request.POST.get("name", "").strip()
                if not name:
                    raise ValueError("Route name is required.")
                route.post = post
                route.name = name
                route.expected_duration_minutes = parse_int_field(
                    request.POST.get("expected_duration_minutes") or 30,
                    label="Expected duration",
                    min_value=1,
                )
                route.is_active = not bool(request.POST.get("inactive"))
                route.save(update_fields=["post", "name", "expected_duration_minutes", "is_active", "updated_at"])
                route.patrolroutecheckpoint_set.all().delete()
                for index, checkpoint_id in enumerate(request.POST.getlist("checkpoint_ids"), start=1):
                    checkpoint = Checkpoint.objects.filter(pk=checkpoint_id, post=post).first()
                    if checkpoint:
                        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=index)
                messages.success(request, "Patrol route updated.")
            elif action == "delete_route":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                route.delete()
                messages.success(request, "Patrol route deleted.")
            elif action == "update_round":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("round_id"))
                next_status = request.POST.get("status") or PatrolRound.Status.SCHEDULED
                patrol_round.route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                patrol_round.assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                patrol_round.scheduled_start = parse_datetime_field(request.POST.get("scheduled_start"), label="Scheduled start")
                patrol_round.scheduled_end = parse_datetime_field(request.POST.get("scheduled_end"), label="Scheduled end")
                patrol_round.save(
                    update_fields=[
                        "route",
                        "assignment",
                        "scheduled_start",
                        "scheduled_end",
                        "updated_at",
                    ]
                )
                if next_status != patrol_round.status:
                    transition_patrol_round(patrol_round, next_status)
                messages.success(request, "Patrol round updated.")
            elif action == "delete_round":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("round_id"))
                patrol_round.delete()
                messages.success(request, "Patrol round deleted.")
            elif action == "delete_scan":
                scan = get_object_or_404(CheckpointScan, pk=request.POST.get("scan_id"))
                scan.delete()
                messages.success(request, "Checkpoint scan deleted.")
            elif action == "update_scan":
                scan = get_object_or_404(CheckpointScan, pk=request.POST.get("scan_id"))
                scan.patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("patrol_round_id"))
                scan.checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                scan.guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                scan.scanned_at = (
                    parse_datetime_field(request.POST.get("scanned_at"), label="Scanned time")
                    if request.POST.get("scanned_at")
                    else scan.scanned_at
                )
                scan.latitude = request.POST.get("latitude") or None
                scan.longitude = request.POST.get("longitude") or None
                scan.accuracy_m = request.POST.get("accuracy_m") or None
                scan.within_geofence = bool(request.POST.get("within_geofence"))
                scan.save()
                messages.success(request, "Checkpoint scan updated.")
            elif action == "checkpoint":
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                Checkpoint.objects.create(
                    post=post,
                    name=request.POST.get("name", "").strip(),
                    code=request.POST.get("code", "").strip(),
                    checkpoint_type=request.POST.get("checkpoint_type") or Checkpoint.CheckpointType.QR,
                    geofence_radius_m=parse_int_field(request.POST.get("geofence_radius_m") or 50, label="Geofence radius", min_value=1),
                )
                messages.success(request, "Checkpoint created.")
            elif action == "route":
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                route = PatrolRoute.objects.create(
                    post=post,
                    name=request.POST.get("name", "").strip(),
                    expected_duration_minutes=parse_int_field(request.POST.get("expected_duration_minutes") or 30, label="Expected duration", min_value=1),
                )
                for index, checkpoint_id in enumerate(request.POST.getlist("checkpoint_ids"), start=1):
                    checkpoint = Checkpoint.objects.filter(pk=checkpoint_id, post=post).first()
                    if checkpoint:
                        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=index)
                messages.success(request, "Patrol route created.")
            elif action == "round":
                route = get_object_or_404(PatrolRoute, pk=request.POST.get("route_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                PatrolRound.objects.create(
                    route=route,
                    assignment=assignment,
                    scheduled_start=parse_datetime_field(request.POST.get("scheduled_start"), label="Scheduled start"),
                    scheduled_end=parse_datetime_field(request.POST.get("scheduled_end"), label="Scheduled end"),
                )
                messages.success(request, "Patrol round scheduled.")
            elif action == "scan":
                patrol_round = get_object_or_404(PatrolRound, pk=request.POST.get("patrol_round_id"))
                checkpoint = get_object_or_404(Checkpoint, pk=request.POST.get("checkpoint_id"))
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                CheckpointScan.objects.create(
                    patrol_round=patrol_round,
                    checkpoint=checkpoint,
                    guard=guard,
                    scanned_at=parse_datetime_field(request.POST.get("scanned_at"), label="Scanned time")
                    if request.POST.get("scanned_at")
                    else timezone.now(),
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    within_geofence=bool(request.POST.get("within_geofence")),
                )
                if patrol_round.status == PatrolRound.Status.SCHEDULED:
                    transition_patrol_round(patrol_round, PatrolRound.Status.IN_PROGRESS)
                messages.success(request, "Checkpoint scan recorded.")
            else:
                messages.error(request, "Unsupported patrol action.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-patrols")


class GuardingPatrolCompleteView(StaffRequiredMixin, View):
    def post(self, request, round_id):
        patrol_round = get_object_or_404(PatrolRound, pk=round_id)
        try:
            complete_patrol_round(patrol_round)
            messages.success(request, "Patrol round completed.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:guarding-patrols")


class GuardingCheckpointQrView(StaffRequiredMixin, View):
    def get(self, request, checkpoint_id):
        import qrcode
        import qrcode.image.svg

        checkpoint = get_object_or_404(Checkpoint.objects.select_related("post", "post__site"), pk=checkpoint_id)
        payload = json.dumps(
            {
                "type": "guard_checkpoint",
                "checkpoint_id": str(checkpoint.id),
                "code": checkpoint.code,
                "site_id": str(checkpoint.post.site_id),
                "site": checkpoint.post.site.name,
                "post_id": str(checkpoint.post_id),
                "post": checkpoint.post.name,
            },
            separators=(",", ":"),
        )
        image = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage)
        response = HttpResponse(content_type="image/svg+xml")
        response["Content-Disposition"] = f'inline; filename="checkpoint-{checkpoint.id}.svg"'
        image.save(response)
        return response


class GuardingPatrolProofExportView(StaffRequiredMixin, View):
    def get(self, request):
        rounds = (
            PatrolRound.objects.select_related(
                "route",
                "route__post",
                "route__post__site",
                "assignment",
                "assignment__guard",
            )
            .prefetch_related("scans__checkpoint", "scans__guard")
            .order_by("-scheduled_start")[:1000]
        )
        rows = []
        for patrol_round in rounds:
            scans = list(patrol_round.scans.all())
            rows.append(
                [
                    patrol_round.id,
                    patrol_round.route.post.site.name,
                    patrol_round.route.post.name,
                    patrol_round.route.name,
                    patrol_round.assignment.guard.full_name if patrol_round.assignment else "",
                    patrol_round.get_status_display(),
                    patrol_round.scheduled_start,
                    patrol_round.scheduled_end,
                    patrol_round.started_at,
                    patrol_round.completed_at,
                    len(scans),
                    "; ".join(
                        f"{scan.checkpoint.name} ({scan.scanned_at:%Y-%m-%d %H:%M})"
                        for scan in sorted(scans, key=lambda item: item.scanned_at)
                    ),
                ]
            )
        if request.GET.get("format") == "pdf" and rounds:
            from django.http import HttpResponse

            from apps.guarding.reports.pdf import render_patrol_round_pdf

            patrol_round = rounds[0]
            pdf_bytes = render_patrol_round_pdf(patrol_round)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="patrol-{patrol_round.id}.pdf"'
            return response

        return csv_response(
            "guarding-patrol-proof.csv",
            [
                "round_id",
                "site",
                "post",
                "route",
                "guard",
                "status",
                "scheduled_start",
                "scheduled_end",
                "started_at",
                "completed_at",
                "scan_count",
                "scans",
            ],
            rows,
        )


