"""Unified profile payload for mobile and API clients."""

from __future__ import annotations

from django.contrib.auth.models import User

from .models import CustomerProfile
from .serializers import CustomerProfileSerializer, UserSerializer


def resolve_account_kind(user: User) -> str:
    if user.is_staff or user.is_superuser:
        return "staff"
    from apps.guarding.models import GuardProfile

    if GuardProfile.objects.filter(user=user).exists():
        return "guard"
    return "customer"


def build_user_profile_payload(user: User) -> dict:
    account_kind = resolve_account_kind(user)
    profile = getattr(user, "customer_profile", None)
    guard_profile_id = None
    guard_employee_number = ""

    if account_kind == "guard":
        from apps.guarding.models import GuardProfile

        guard = GuardProfile.objects.filter(user=user).only("id", "employee_number").first()
        if guard:
            guard_profile_id = str(guard.id)
            guard_employee_number = guard.employee_number

    if profile:
        data = CustomerProfileSerializer(profile).data
    else:
        data = {
            "user": UserSerializer(user).data,
            "phone_number": "",
            "is_mobile_user": False,
        }

    data["account_kind"] = account_kind
    data["guard_profile_id"] = guard_profile_id
    data["guard_employee_number"] = guard_employee_number
    data["is_staff"] = bool(user.is_staff or user.is_superuser)
    return data
