"""Shared mixins for dashboard views."""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from apps.guarding.models import ClientPortalAccess, DispatchTask, GuardApplicant, GuardPanicAlert, GuardPost, GuardProfile, WelfareCheck
from apps.guarding.services import count_non_compliant_active_guards


class GuardingClientRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return bool(
            self.request.user.is_authenticated
            and ClientPortalAccess.objects.filter(user=self.request.user).exists()
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={self.request.get_full_path()}"
            return redirect(login_url)
        return HttpResponseForbidden("Guarding client access required.")


class GuardingOverviewMixin:
    def get_guarding_counts(self):
        active_dispatch_statuses = [
            DispatchTask.Status.OPEN,
            DispatchTask.Status.ASSIGNED,
            DispatchTask.Status.ACCEPTED,
            DispatchTask.Status.EN_ROUTE,
            DispatchTask.Status.ARRIVED,
        ]
        counts = {
            "guards": GuardProfile.objects.filter(status=GuardProfile.Status.ACTIVE).count(),
            "applicants": GuardApplicant.objects.exclude(
                status__in=[
                    GuardApplicant.Status.HIRED,
                    GuardApplicant.Status.REJECTED,
                    GuardApplicant.Status.WITHDRAWN,
                ]
            ).count(),
            "posts": GuardPost.objects.filter(is_active=True).count(),
            "open_dispatch": DispatchTask.objects.filter(status__in=active_dispatch_statuses).count(),
            "open_panic": GuardPanicAlert.objects.filter(status=GuardPanicAlert.Status.OPEN).count(),
            "welfare_due": WelfareCheck.objects.filter(
                status__in=[WelfareCheck.Status.PENDING, WelfareCheck.Status.ESCALATED]
            ).count(),
            "non_compliant_guards": count_non_compliant_active_guards(),
        }
        try:
            from apps.guarding.asset_services import asset_analytics_summary

            asset_stats = asset_analytics_summary()
            counts["open_manifests"] = asset_stats["open_manifests"]
            counts["assets_out"] = asset_stats["units_out"]
            counts["overdue_asset_returns"] = asset_stats["overdue_returns"]
        except Exception:
            counts["open_manifests"] = 0
            counts["assets_out"] = 0
            counts["overdue_asset_returns"] = 0
        return counts
