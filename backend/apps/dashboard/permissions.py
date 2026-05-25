from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.permissions import (
    user_can_access_console,
    user_can_access_console_route,
    user_has_console_permission,
)
from apps.accounts.rbac import Perm


class StaffRequiredMixin(UserPassesTestMixin):
    """Staff session required; optional ``required_console_permission`` on the view."""

    required_console_permission: str | None = None

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated or not user.is_staff:
            return False
        if not user_can_access_console(user):
            return False
        codename = self.required_console_permission
        if codename:
            return user_has_console_permission(user, codename)
        url_name = getattr(self.request.resolver_match, "url_name", None)
        return user_can_access_console_route(user, url_name)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={self.request.get_full_path()}"
            return redirect(login_url)
        if self.request.user.is_staff and not user_can_access_console(self.request.user):
            return HttpResponseForbidden("Your operator account does not have console access.")
        codename = self.required_console_permission or permission_for_view(self)
        if codename and self.request.user.is_staff:
            messages.error(
                self.request,
                "You do not have permission to access this section of the console.",
            )
            return redirect("dashboard:home")
        return HttpResponseForbidden("Staff access required.")


def permission_for_view(view) -> str | None:
    from apps.accounts.permissions import permission_for_console_route

    url_name = getattr(view.request.resolver_match, "url_name", None)
    return permission_for_console_route(url_name)


class SuperuserRequiredMixin(StaffRequiredMixin):
    """Staff user management — requires manage_staff (superusers always pass)."""

    required_console_permission = Perm.MANAGE_STAFF

    def test_func(self):
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return True
        return super().test_func()

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={self.request.get_full_path()}"
            return redirect(login_url)
        return HttpResponseForbidden("Permission denied: staff user management required.")
