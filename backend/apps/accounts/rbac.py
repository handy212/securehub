"""
Operator console RBAC: roles, permission codenames, and route mapping.

Site-scoped customer access (CustomerSiteAccess) and guarding client portal
(ClientPortalAccess) remain separate domain models in their respective apps.
"""

from __future__ import annotations

from typing import FrozenSet


class OperatorRole:
    PLATFORM_ADMIN = "platform_admin"
    OPERATIONS = "operations"
    GUARDING = "guarding"
    DISPATCHER = "dispatcher"
    BILLING = "billing"
    SUPPORT = "support"
    AUDITOR = "auditor"

    CHOICES = (
        (PLATFORM_ADMIN, "Platform administrator"),
        (OPERATIONS, "Operations"),
        (GUARDING, "Guarding"),
        (DISPATCHER, "Dispatcher"),
        (BILLING, "Billing"),
        (SUPPORT, "Support"),
        (AUDITOR, "Auditor (read-only)"),
    )


# Permission codenames (console.*)
class Perm:
    ACCESS = "console.access"
    VIEW_DASHBOARD = "console.view_dashboard"
    VIEW_SITES = "console.view_sites"
    MANAGE_SITES = "console.manage_sites"
    VIEW_EMERGENCY = "console.view_emergency"
    MANAGE_EMERGENCY = "console.manage_emergency"
    VIEW_GUARDING = "console.view_guarding"
    MANAGE_GUARDING = "console.manage_guarding"
    VIEW_BILLING = "console.view_billing"
    MANAGE_BILLING = "console.manage_billing"
    VIEW_CUSTOMERS = "console.view_customers"
    MANAGE_CUSTOMERS = "console.manage_customers"
    VIEW_LOGS = "console.view_logs"
    MANAGE_BROADCAST = "console.manage_broadcast"
    MANAGE_SETTINGS = "console.manage_settings"
    MANAGE_STAFF = "console.manage_staff"
    GLOBAL_SYNC = "console.global_sync"


ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        Perm.ACCESS,
        Perm.VIEW_DASHBOARD,
        Perm.VIEW_SITES,
        Perm.MANAGE_SITES,
        Perm.VIEW_EMERGENCY,
        Perm.MANAGE_EMERGENCY,
        Perm.VIEW_GUARDING,
        Perm.MANAGE_GUARDING,
        Perm.VIEW_BILLING,
        Perm.MANAGE_BILLING,
        Perm.VIEW_CUSTOMERS,
        Perm.MANAGE_CUSTOMERS,
        Perm.VIEW_LOGS,
        Perm.MANAGE_BROADCAST,
        Perm.MANAGE_SETTINGS,
        Perm.MANAGE_STAFF,
        Perm.GLOBAL_SYNC,
    }
)

_READ_OPS = frozenset(
    {
        Perm.ACCESS,
        Perm.VIEW_DASHBOARD,
        Perm.VIEW_SITES,
        Perm.VIEW_EMERGENCY,
        Perm.VIEW_GUARDING,
        Perm.VIEW_BILLING,
        Perm.VIEW_CUSTOMERS,
        Perm.VIEW_LOGS,
    }
)

_OPERATIONS = _READ_OPS | {
    Perm.MANAGE_SITES,
    Perm.MANAGE_EMERGENCY,
    Perm.MANAGE_CUSTOMERS,
    Perm.MANAGE_BROADCAST,
    Perm.GLOBAL_SYNC,
}

_GUARDING = _READ_OPS | {
    Perm.MANAGE_GUARDING,
}

_DISPATCHER = frozenset(
    {
        Perm.ACCESS,
        Perm.VIEW_DASHBOARD,
        Perm.VIEW_EMERGENCY,
        Perm.MANAGE_EMERGENCY,
        Perm.VIEW_GUARDING,
        Perm.MANAGE_GUARDING,
        Perm.VIEW_SITES,
    }
)

_BILLING = frozenset(
    {
        Perm.ACCESS,
        Perm.VIEW_DASHBOARD,
        Perm.VIEW_BILLING,
        Perm.MANAGE_BILLING,
        Perm.VIEW_CUSTOMERS,
        Perm.VIEW_SITES,
    }
)

_SUPPORT = frozenset(
    {
        Perm.ACCESS,
        Perm.VIEW_DASHBOARD,
        Perm.VIEW_SITES,
        Perm.VIEW_CUSTOMERS,
        Perm.MANAGE_CUSTOMERS,
        Perm.VIEW_EMERGENCY,
        Perm.VIEW_LOGS,
        Perm.MANAGE_BROADCAST,
    }
)

ROLE_PERMISSIONS: dict[str, FrozenSet[str]] = {
    OperatorRole.PLATFORM_ADMIN: ALL_PERMISSIONS,
    OperatorRole.OPERATIONS: frozenset(_OPERATIONS),
    OperatorRole.GUARDING: frozenset(_GUARDING),
    OperatorRole.DISPATCHER: frozenset(_DISPATCHER),
    OperatorRole.BILLING: frozenset(_BILLING),
    OperatorRole.SUPPORT: frozenset(_SUPPORT),
    OperatorRole.AUDITOR: frozenset(_READ_OPS),
}


def permissions_for_role(role: str) -> FrozenSet[str]:
    return ROLE_PERMISSIONS.get(role, frozenset({Perm.ACCESS}))


def default_role_for_user(*, is_superuser: bool) -> str:
    if is_superuser:
        return OperatorRole.PLATFORM_ADMIN
    return OperatorRole.OPERATIONS


# dashboard url_name -> required permission (view/manage split where routes differ)
CONSOLE_ROUTE_PERMISSIONS: dict[str, str] = {
    "help-index": Perm.ACCESS,
    "help-page": Perm.ACCESS,
    "home": Perm.VIEW_DASHBOARD,
    "site-map": Perm.VIEW_SITES,
    "map-zones": Perm.MANAGE_SITES,
    "map-zone-update": Perm.MANAGE_SITES,
    "map-zone-delete": Perm.MANAGE_SITES,
    "guard-map-poll": Perm.VIEW_GUARDING,
    "emergency": Perm.VIEW_EMERGENCY,
    "emergency-assign": Perm.MANAGE_EMERGENCY,
    "emergency-action": Perm.MANAGE_EMERGENCY,
    "emergency-services": Perm.MANAGE_EMERGENCY,
    "emergency-plan-create": Perm.MANAGE_EMERGENCY,
    "emergency-plan-update": Perm.MANAGE_EMERGENCY,
    "emergency-plan-delete": Perm.MANAGE_EMERGENCY,
    "site-emergency-create": Perm.MANAGE_EMERGENCY,
    "account-emergency-create": Perm.MANAGE_EMERGENCY,
    "site-emergency-update": Perm.MANAGE_EMERGENCY,
    "site-emergency-delete": Perm.MANAGE_EMERGENCY,
    "account-emergency-update": Perm.MANAGE_EMERGENCY,
    "account-emergency-delete": Perm.MANAGE_EMERGENCY,
    "guarding-overview": Perm.VIEW_GUARDING,
    "guarding-live-map": Perm.VIEW_GUARDING,
    "guarding-analytics": Perm.VIEW_GUARDING,
    "guarding-applicants": Perm.VIEW_GUARDING,
    "guarding-applicant-hire": Perm.MANAGE_GUARDING,
    "guarding-guards": Perm.VIEW_GUARDING,
    "guarding-assets": Perm.VIEW_GUARDING,
    "guarding-posts": Perm.VIEW_GUARDING,
    "guarding-shifts": Perm.VIEW_GUARDING,
    "guarding-patrols": Perm.VIEW_GUARDING,
    "guarding-patrols-export": Perm.VIEW_GUARDING,
    "guarding-patrol-complete": Perm.MANAGE_GUARDING,
    "guarding-checkpoint-qr": Perm.VIEW_GUARDING,
    "guarding-reports": Perm.VIEW_GUARDING,
    "guarding-reports-export": Perm.VIEW_GUARDING,
    "guarding-report-review": Perm.MANAGE_GUARDING,
    "guarding-backoffice": Perm.MANAGE_GUARDING,
    "guarding-timesheets-export": Perm.MANAGE_GUARDING,
    "guarding-dispatch": Perm.VIEW_GUARDING,
    "guarding-dispatch-poll": Perm.VIEW_GUARDING,
    "guarding-panic-action": Perm.MANAGE_GUARDING,
    "guarding-dispatch-action": Perm.MANAGE_GUARDING,
    "sites": Perm.VIEW_SITES,
    "site-console": Perm.VIEW_SITES,
    "site-action": Perm.MANAGE_SITES,
    "update-site": Perm.MANAGE_SITES,
    "provision-site": Perm.MANAGE_SITES,
    "register-panel": Perm.MANAGE_SITES,
    "delete-site": Perm.MANAGE_SITES,
    "hik-add-device": Perm.MANAGE_SITES,
    "hik-remove-device": Perm.MANAGE_SITES,
    "onboard-client": Perm.MANAGE_SITES,
    "site-access-update": Perm.MANAGE_SITES,
    "site-access-delete": Perm.MANAGE_SITES,
    "event-pictures": Perm.VIEW_SITES,
    "logs": Perm.VIEW_LOGS,
    "user-list": Perm.MANAGE_STAFF,
    "user-create": Perm.MANAGE_STAFF,
    "user-update": Perm.MANAGE_STAFF,
    "user-delete": Perm.MANAGE_STAFF,
    "customer-list": Perm.VIEW_CUSTOMERS,
    "customer-create": Perm.MANAGE_CUSTOMERS,
    "customer-update": Perm.MANAGE_CUSTOMERS,
    "customer-delete": Perm.MANAGE_CUSTOMERS,
    "customer-groups": Perm.MANAGE_CUSTOMERS,
    "customer-group-update": Perm.MANAGE_CUSTOMERS,
    "customer-group-delete": Perm.MANAGE_CUSTOMERS,
    "settings": Perm.MANAGE_SETTINGS,
    "global-sync": Perm.GLOBAL_SYNC,
    "subscriptions": Perm.VIEW_BILLING,
    "subscription-create": Perm.MANAGE_BILLING,
    "packages": Perm.MANAGE_BILLING,
    "package-update": Perm.MANAGE_BILLING,
    "package-delete": Perm.MANAGE_BILLING,
    "subscription-update": Perm.MANAGE_BILLING,
    "payment-update": Perm.MANAGE_BILLING,
    "payment-delete": Perm.MANAGE_BILLING,
    "subscription-pay": Perm.MANAGE_BILLING,
    "subscription-suspend": Perm.MANAGE_BILLING,
    "subscription-cancel": Perm.MANAGE_BILLING,
    "subscription-reactivate": Perm.MANAGE_BILLING,
    "broadcast": Perm.MANAGE_BROADCAST,
    "broadcast-update": Perm.MANAGE_BROADCAST,
    "broadcast-resend": Perm.MANAGE_BROADCAST,
    "broadcast-delete": Perm.MANAGE_BROADCAST,
}
