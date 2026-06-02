from __future__ import annotations

from django.contrib.auth.models import User

from rest_framework.permissions import BasePermission

from .models import StaffOperatorProfile
from .rbac import CONSOLE_ROUTE_PERMISSIONS, OperatorRole, Perm, permissions_for_role


def user_bypasses_console_rbac(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


def get_operator_profile(user) -> StaffOperatorProfile | None:
    if not user or not user.is_authenticated or not user.is_staff:
        return None
    try:
        return user.operator_profile
    except StaffOperatorProfile.DoesNotExist:
        return None


def ensure_operator_profile(user: User) -> StaffOperatorProfile:
    profile, _ = StaffOperatorProfile.objects.get_or_create(
        user=user,
        defaults={"role": StaffOperatorProfile.default_role_for_user(user)},
    )
    return profile


def get_operator_role(user) -> str | None:
    if not user or not user.is_authenticated or not user.is_staff:
        return None
    if user_bypasses_console_rbac(user):
        return OperatorRole.PLATFORM_ADMIN
    profile = get_operator_profile(user)
    if profile:
        return profile.role
    return StaffOperatorProfile.default_role_for_user(user)


def user_has_console_permission(user, permission: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if not user.is_staff:
        return False
    if user_bypasses_console_rbac(user):
        return True
    role = get_operator_role(user)
    if not role:
        return False
    return permission in permissions_for_role(role)


def user_can_access_console(user) -> bool:
    return user_has_console_permission(user, Perm.ACCESS)


def permission_for_console_route(url_name: str | None) -> str | None:
    if not url_name:
        return None
    return CONSOLE_ROUTE_PERMISSIONS.get(url_name)


def user_can_access_console_route(user, url_name: str | None) -> bool:
    required = permission_for_console_route(url_name)
    if required is None:
        return user_can_access_console(user)
    return user_has_console_permission(user, required)


class HasConsolePermission(BasePermission):
    """DRF permission: set ``required_console_permission`` on the view."""

    def has_permission(self, request, view):
        codename = getattr(view, "required_console_permission", Perm.ACCESS)
        return user_has_console_permission(request.user, codename)


class IsConsoleStaff(BasePermission):
    def has_permission(self, request, view):
        return user_can_access_console(request.user)
