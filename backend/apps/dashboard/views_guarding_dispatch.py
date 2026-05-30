"""Guarding console: dispatch."""

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

class GuardingLiveMapView(StaffRequiredMixin, View):
    """Legacy route — field guards live on the global map."""

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('dashboard:site-map')}?focus=guards")


class GuardingAnalyticsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/analytics.html"

    def get_context_data(self, **kwargs):
        from apps.guarding.analytics import guarding_kpis

        context = super().get_context_data(**kwargs)
        days = int(self.request.GET.get("days", 7))
        context["kpis"] = guarding_kpis(days=days)
        context["days"] = days
        context["counts"] = self.get_guarding_counts()
        return context


class GuardingDispatchView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/dispatch.html"
    _DISPATCH_ACTION_TABS = {
        "save_dispatch_policy": "policies",
        "panic_alert": "sos",
        "update_panic_alert": "sos",
        "delete_panic_alert": "sos",
        "update_task": "tasks",
        "delete_task": "tasks",
        "task": "tasks",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["panic_alerts"] = GuardPanicAlert.objects.select_related("guard", "site", "assignment").order_by("-created_at")[:100]
        context["dispatch_tasks"] = DispatchTask.objects.select_related("site", "assigned_guard", "panic_alert").order_by("-created_at")[:200]
        context["guards"] = GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).order_by("last_name", "first_name")
        context["sites"] = Site.objects.order_by("name")
        context["assignments"] = ShiftAssignment.objects.select_related("shift", "shift__post", "guard").order_by("-shift__starts_at")[:200]
        context["priorities"] = DispatchTask.Priority.choices
        context["panic_statuses"] = GuardPanicAlert.Status.choices
        policies = {
            policy.site_id: policy
            for policy in SiteGuardDispatchPolicy.objects.select_related("site")
        }
        context["site_dispatch_policies"] = [
            {"site": site, "policy": policies.get(site.id)}
            for site in Site.objects.order_by("name")
        ]
        context["alarm_severity_options"] = [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ]
        context["counts"] = self.get_guarding_counts()
        counts = context["counts"]
        context["dispatch_tab_counts"] = {
            "open_panic": counts["open_panic"],
            "open_tasks": counts["open_dispatch"],
            "policy_sites": len(context["site_dispatch_policies"]),
            "active_policies": SiteGuardDispatchPolicy.objects.filter(is_active=True).count(),
        }
        return context

    def post(self, request):
        try:
            action = request.POST.get("action", "task")
            if action == "save_dispatch_policy":
                site = get_object_or_404(Site, pk=request.POST.get("site_id"))
                policy, _ = SiteGuardDispatchPolicy.objects.get_or_create(site=site)
                policy.is_active = bool(request.POST.get("is_active"))
                policy.auto_from_emergency = bool(request.POST.get("auto_from_emergency"))
                policy.auto_from_alarm = bool(request.POST.get("auto_from_alarm"))
                policy.auto_assign_nearest = bool(request.POST.get("auto_assign_nearest"))
                policy.default_priority = (
                    request.POST.get("default_priority") or DispatchTask.Priority.HIGH
                )
                policy.alarm_severities = [
                    value for value in request.POST.getlist("alarm_severities") if value
                ]
                policy.full_clean()
                policy.save()
                messages.success(request, f"Auto-dispatch policy saved for {site.name}.")
            elif action == "panic_alert":
                guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                if site is None and assignment:
                    site = assignment.shift.post.site
                GuardPanicAlert.objects.create(
                    guard=guard,
                    assignment=assignment,
                    site=site,
                    status=GuardPanicAlert.Status.OPEN,
                    latitude=request.POST.get("latitude") or None,
                    longitude=request.POST.get("longitude") or None,
                    accuracy_m=request.POST.get("accuracy_m") or None,
                    note=request.POST.get("note", "").strip(),
                )
                messages.success(request, "Panic alert created.")
            elif action == "update_panic_alert":
                alert = get_object_or_404(GuardPanicAlert, pk=request.POST.get("alert_id"))
                assignment = ShiftAssignment.objects.filter(pk=request.POST.get("assignment_id")).first()
                next_status = request.POST.get("status") or GuardPanicAlert.Status.OPEN
                if next_status != alert.status:
                    ensure_panic_alert_status_transition(alert, next_status)
                alert.guard = get_object_or_404(GuardProfile, pk=request.POST.get("guard_id"))
                alert.assignment = assignment
                alert.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                alert.latitude = request.POST.get("latitude") or None
                alert.longitude = request.POST.get("longitude") or None
                alert.accuracy_m = request.POST.get("accuracy_m") or None
                alert.note = request.POST.get("note", "").strip()
                alert.save(update_fields=["guard", "assignment", "site", "latitude", "longitude", "accuracy_m", "note", "updated_at"])
                if next_status != alert.status:
                    transition_panic_alert(alert, status=next_status, actor=request.user)
                messages.success(request, "Panic alert updated.")
            elif action == "delete_panic_alert":
                alert = get_object_or_404(GuardPanicAlert, pk=request.POST.get("alert_id"))
                alert.delete()
                messages.success(request, "Panic alert deleted.")
            elif action == "update_task":
                task = get_object_or_404(DispatchTask, pk=request.POST.get("task_id"))
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                title = request.POST.get("title", "").strip()
                if not title:
                    raise ValueError("Dispatch title is required.")
                was_unassigned = task.assigned_guard_id is None
                task.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                task.assigned_guard = guard
                task.priority = request.POST.get("priority") or DispatchTask.Priority.MEDIUM
                task.title = title
                task.description = request.POST.get("description", "").strip()
                if guard and was_unassigned:
                    task.assigned_at = timezone.now()
                task.save(
                    update_fields=[
                        "site",
                        "assigned_guard",
                        "priority",
                        "title",
                        "description",
                        "assigned_at",
                        "updated_at",
                    ]
                )
                messages.success(request, "Dispatch task updated.")
            elif action == "delete_task":
                task = get_object_or_404(DispatchTask, pk=request.POST.get("task_id"))
                task.delete()
                messages.success(request, "Dispatch task deleted.")
            else:
                site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
                DispatchTask.objects.create(
                    site=site,
                    assigned_guard=guard,
                    assigned_at=timezone.now() if guard else None,
                    status=DispatchTask.Status.ASSIGNED if guard else DispatchTask.Status.OPEN,
                    priority=request.POST.get("priority") or DispatchTask.Priority.MEDIUM,
                    title=request.POST.get("title", "").strip(),
                    description=request.POST.get("description", "").strip(),
                    created_by=request.user,
                )
                messages.success(request, "Dispatch task created.")
        except Exception as exc:
            messages.error(request, str(exc))
        tab = self._DISPATCH_ACTION_TABS.get(action)
        if tab:
            return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab={tab}")
        return redirect("dashboard:guarding-dispatch")


class GuardingPanicActionView(StaffRequiredMixin, View):
    def post(self, request, alert_id, action):
        alert = get_object_or_404(GuardPanicAlert, pk=alert_id)
        try:
            if action == "acknowledge":
                acknowledge_panic_alert(alert, actor=request.user)
            elif action == "resolve":
                resolve_panic_alert(alert, actor=request.user)
            else:
                messages.error(request, "Unsupported panic action.")
                return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=sos")
            messages.success(request, "Panic alert updated.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=sos")


class GuardingDispatchActionView(StaffRequiredMixin, View):
    action_statuses = {
        "assign": DispatchTask.Status.ASSIGNED,
        "accept": DispatchTask.Status.ACCEPTED,
        "en-route": DispatchTask.Status.EN_ROUTE,
        "arrive": DispatchTask.Status.ARRIVED,
        "resolve": DispatchTask.Status.RESOLVED,
        "cancel": DispatchTask.Status.CANCELLED,
    }

    def post(self, request, task_id, action):
        task = get_object_or_404(DispatchTask, pk=task_id)
        if action not in self.action_statuses:
            messages.error(request, "Unsupported dispatch action.")
            return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=tasks")
        guard = GuardProfile.objects.filter(pk=request.POST.get("guard_id")).first()
        if guard:
            task.assigned_guard = guard
            task.save(update_fields=["assigned_guard", "updated_at"])
        try:
            transition_dispatch_task(
                task,
                status=self.action_statuses[action],
                actor=request.user,
                note=request.POST.get("note", "").strip(),
            )
            messages.success(request, "Dispatch task updated.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('dashboard:guarding-dispatch')}?tab=tasks")

