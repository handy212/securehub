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

class EmergencyServiceManagementView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/emergency/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_statuses = [EmergencyServiceStatus.ACTIVE, EmergencyServiceStatus.OVERDUE]
        site_services = SiteEmergencyService.objects.select_related("site", "plan").order_by("site__name")
        account_services = AccountEmergencyService.objects.select_related("user", "plan").order_by("user__username")
        context["plans"] = EmergencyServicePlan.objects.all()
        context["active_plans"] = EmergencyServicePlan.objects.filter(is_active=True).order_by("monthly_rate")
        context["site_services"] = site_services
        context["account_services"] = account_services
        context["available_sites"] = Site.objects.filter(emergency_service__isnull=True).order_by("name")
        context["available_customers"] = User.objects.filter(
            is_staff=False,
            emergency_service__isnull=True,
        ).order_by("username")
        context["statuses"] = EmergencyServiceStatus.choices
        context["site_mrr"] = (
            SiteEmergencyService.objects.filter(status__in=active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["account_mrr"] = (
            AccountEmergencyService.objects.filter(status__in=active_statuses)
            .aggregate(total=Sum("monthly_rate"))["total"]
            or Decimal("0.00")
        )
        context["total_emergency_mrr"] = context["site_mrr"] + context["account_mrr"]
        context["active_site_count"] = SiteEmergencyService.objects.filter(status__in=active_statuses).count()
        context["active_account_count"] = AccountEmergencyService.objects.filter(status__in=active_statuses).count()
        return context


class CreateEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        rate = request.POST.get("monthly_rate", "").strip()
        if not name or not rate:
            messages.error(request, "Plan name and monthly rate are required.")
            return redirect("dashboard:emergency-services")
        try:
            parsed_rate = parse_decimal_field(rate, label="Monthly rate", min_value=Decimal("0.00"))
            EmergencyServicePlan.objects.create(
                name=name,
                monthly_rate=parsed_rate,
                description=request.POST.get("description", "").strip(),
                is_active=request.POST.get("is_active", "1") == "1",
            )
            messages.success(request, f"Emergency plan '{name}' created.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class UpdateEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request, plan_id):
        plan = get_object_or_404(EmergencyServicePlan, pk=plan_id)
        name = request.POST.get("name", "").strip()
        rate = request.POST.get("monthly_rate", "").strip()
        if not name or not rate:
            messages.error(request, "Plan name and monthly rate are required.")
            return redirect("dashboard:emergency-services")
        try:
            plan.name = name
            plan.monthly_rate = parse_decimal_field(rate, label="Monthly rate", min_value=Decimal("0.00"))
            plan.description = request.POST.get("description", "").strip()
            plan.is_active = request.POST.get("is_active") == "1"
            plan.save(update_fields=["name", "monthly_rate", "description", "is_active"])
            messages.success(request, f"Emergency plan '{plan.name}' updated.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteEmergencyPlanView(StaffRequiredMixin, View):
    def post(self, request, plan_id):
        plan = get_object_or_404(EmergencyServicePlan, pk=plan_id)
        if plan.site_services.exists() or plan.account_services.exists():
            messages.error(request, f"Cannot delete '{plan.name}' while it is linked to emergency services.")
            return redirect("dashboard:emergency-services")
        name = plan.name
        plan.delete()
        messages.success(request, f"Emergency plan '{name}' deleted.")
        return redirect("dashboard:emergency-services")


def parse_emergency_service_payload(request):
    plan_id = request.POST.get("plan_id", "").strip()
    plan = EmergencyServicePlan.objects.filter(pk=plan_id).first() if plan_id else None
    monthly_rate = request.POST.get("monthly_rate", "").strip()
    if not monthly_rate and plan:
        monthly_rate = str(plan.monthly_rate)
    if not monthly_rate:
        raise ValueError("Monthly rate is required.")
    status = request.POST.get("status", EmergencyServiceStatus.ACTIVE).strip()
    valid_statuses = {choice[0] for choice in EmergencyServiceStatus.choices}
    if status not in valid_statuses:
        raise ValueError("Please choose a valid emergency service status.")
    next_due_date = request.POST.get("next_due_date", "").strip()
    return {
        "plan": plan,
        "monthly_rate": parse_decimal_field(monthly_rate, label="Monthly rate", min_value=Decimal("0.00")),
        "status": status,
        "next_due_date": parse_date_field(next_due_date, label="Next due date") if next_due_date else None,
        "notes": request.POST.get("notes", "").strip(),
    }


class CreateSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request):
        site = get_object_or_404(Site, pk=request.POST.get("site_id"))
        if SiteEmergencyService.objects.filter(site=site).exists():
            messages.error(request, f"'{site.name}' already has emergency service configured.")
            return redirect("dashboard:emergency-services")
        try:
            SiteEmergencyService.objects.create(site=site, **parse_emergency_service_payload(request))
            messages.success(request, f"Emergency service enabled for '{site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class CreateAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request):
        user = get_object_or_404(User, pk=request.POST.get("user_id"), is_staff=False)
        if AccountEmergencyService.objects.filter(user=user).exists():
            messages.error(request, f"'{user.username}' already has account emergency service configured.")
            return redirect("dashboard:emergency-services")
        try:
            AccountEmergencyService.objects.create(user=user, **parse_emergency_service_payload(request))
            messages.success(request, f"Emergency service enabled for '{user.username}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class UpdateSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(SiteEmergencyService, pk=service_id)
        try:
            for field, value in parse_emergency_service_payload(request).items():
                setattr(service, field, value)
            service.save(update_fields=["plan", "monthly_rate", "status", "next_due_date", "notes", "updated_at"])
            messages.success(request, f"Updated emergency service for '{service.site.name}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteSiteEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(SiteEmergencyService.objects.select_related("site"), pk=service_id)
        site_name = service.site.name
        service.delete()
        messages.success(request, f"Emergency service removed from '{site_name}'.")
        return redirect("dashboard:emergency-services")


class UpdateAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(AccountEmergencyService, pk=service_id)
        try:
            for field, value in parse_emergency_service_payload(request).items():
                setattr(service, field, value)
            service.save(update_fields=["plan", "monthly_rate", "status", "next_due_date", "notes", "updated_at"])
            messages.success(request, f"Updated emergency service for '{service.user.username}'.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:emergency-services")


class DeleteAccountEmergencyServiceView(StaffRequiredMixin, View):
    def post(self, request, service_id):
        service = get_object_or_404(AccountEmergencyService.objects.select_related("user"), pk=service_id)
        username = service.user.username
        service.delete()
        messages.success(request, f"Emergency service removed from '{username}'.")
        return redirect("dashboard:emergency-services")
