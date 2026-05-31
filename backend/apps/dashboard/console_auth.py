"""Staff console authentication helpers and login view."""

from __future__ import annotations

import secrets

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from apps.accounts.permissions import ensure_operator_profile, user_can_access_console
from apps.accounts.serializers import resolve_username_for_login
from apps.guarding.models import ClientPortalAccess

CONSOLE_LOGIN_ATTEMPT_LIMIT = 5
CONSOLE_LOGIN_LOCKOUT_SECONDS = 300


def request_client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR", "unknown")


def console_login_cache_keys(request, username: str) -> tuple[str, str]:
    client_ip = request_client_ip(request)
    username_value = username.strip().lower() or "unknown"
    return (
        f"console-login:ip:{client_ip}",
        f"console-login:user:{client_ip}:{username_value}",
    )


def console_login_locked(request, username: str) -> bool:
    return any(
        (cache.get(key) or 0) >= CONSOLE_LOGIN_ATTEMPT_LIMIT
        for key in console_login_cache_keys(request, username)
    )


def record_console_login_failure(request, username: str) -> None:
    for key in console_login_cache_keys(request, username):
        attempts = (cache.get(key) or 0) + 1
        cache.set(key, attempts, timeout=CONSOLE_LOGIN_LOCKOUT_SECONDS)


def clear_console_login_failures(request, username: str) -> None:
    for key in console_login_cache_keys(request, username):
        cache.delete(key)


def password_validation_user(
    *,
    username: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    user_id=None,
) -> User:
    return User(
        pk=user_id,
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )


def validate_console_password(password: str, *, user: User) -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValueError(" ".join(exc.messages)) from exc


def generate_compliant_password(*, user: User) -> str:
    for _ in range(10):
        candidate = secrets.token_urlsafe(16)
        try:
            validate_console_password(candidate, user=user)
            return candidate
        except ValueError:
            continue
    raise ValueError(
        "Unable to generate a compliant temporary password. Please provide one manually."
    )


def user_has_guarding_client_access(user: User) -> bool:
    return bool(
        user.is_authenticated
        and not user.is_staff
        and ClientPortalAccess.objects.filter(user=user).exists()
    )


def guarding_client_login_target(next_url: str) -> str:
    if next_url.startswith("/console/client/guarding/"):
        return next_url
    return "/console/client/guarding/"


class ConsoleLoginView(View):
    template_name = "dashboard/auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            if user_has_guarding_client_access(request.user):
                return redirect(guarding_client_login_target(request.GET.get("next", "")))
            return redirect("dashboard:home")
        return render(request, self.template_name, {"next": request.GET.get("next", "/console/")})

    def post(self, request):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next", "/console/")
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/console/"
        if console_login_locked(request, username):
            return render(
                request,
                self.template_name,
                {
                    "error": "Too many sign-in attempts. Please wait a few minutes and try again.",
                    "next": next_url,
                },
            )
        auth_username = resolve_username_for_login(username)
        user = authenticate(request, username=auth_username, password=password)
        has_console_access = bool(user is not None and user.is_staff and user_can_access_console(user))
        has_guarding_client_access = bool(
            user is not None and user_has_guarding_client_access(user)
        )
        if has_console_access or has_guarding_client_access:
            if has_console_access:
                ensure_operator_profile(user)
            clear_console_login_failures(request, username)
            login(request, user)
            if has_guarding_client_access and not has_console_access:
                return redirect(guarding_client_login_target(next_url))
            return redirect(next_url)
        record_console_login_failure(request, username)
        return render(
            request,
            self.template_name,
            {
                "error": "Invalid credentials or insufficient permissions.",
                "next": next_url,
            },
        )
