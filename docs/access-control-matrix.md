# Access control matrix

SecureHub has separate access layers for operators, alarm customers, guarding clients, and field guards. Keep these layers separate unless a feature explicitly bridges them.

## Operator console

Staff users (`is_staff=True`) require a `StaffOperatorProfile`. Superusers bypass console RBAC and behave as platform administrators.

| Role | Main permissions | Typical access |
|------|------------------|----------------|
| `platform_admin` | All `console.*` permissions | Full console, staff management, settings |
| `operations` | Sites, customers, emergency, broadcast, sync | Day-to-day alarm operations |
| `guarding` | View/manage guarding | Guarding operations, shifts, reports, back office |
| `dispatcher` | Emergency + guarding management | Dispatch, panic alerts, command center |
| `billing` | View/manage billing, view customers/sites | Subscriptions, packages, payments |
| `support` | Customers, emergency view, logs, broadcast | Customer care and messaging |
| `auditor` | Read-only operational views | Review without mutation |

Route permissions live in `apps/accounts/rbac.py` as `CONSOLE_ROUTE_PERMISSIONS`. Every staff dashboard route should either be mapped there or intentionally use a non-staff guard such as `GuardingClientRequiredMixin`.

## Alarm customers

Mobile alarm users are regular Django users linked to sites through `CustomerSiteAccess`.

| Role | Site visibility | Alarm control |
|------|-----------------|---------------|
| Owner | Yes | Allowed when `can_control_alarm=True` |
| Manager | Yes | Allowed when `can_control_alarm=True` |
| Viewer | Yes | Never allowed |

Customer API access is site-scoped through `HasSiteAccess`, `CanControlAlarm`, and `IsSubscriptionActive`. Staff and superusers can access all sites through the API.

## Guarding clients

B2B guarding portal users are regular Django users linked to sites through `ClientPortalAccess`.

| Flag | Allows |
|------|--------|
| `can_view_reports` | Approved client-visible field reports |
| `can_view_patrols` | Patrol proof for accessible sites |
| `can_view_attendance` | Shift attendance rows |
| `can_view_guards` | “Know your guard” safe profile summaries |
| `can_acknowledge_reports` | Acknowledge approved reports |

Operator accounts must not be assigned as guarding clients.

## Field guards

Field guards are regular Django users linked one-to-one to `GuardProfile`. Guard mobile endpoints under `/api/v1/guarding/me/` must scope records to the authenticated guard profile.

## Staff APIs

Guarding staff APIs use console-aware permissions rather than plain `IsAdminUser` when the endpoint overlaps operator console work. Mobile guard self-service APIs remain `IsAuthenticated` plus guard-profile scoping.
