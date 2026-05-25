# SecureHub documentation

This folder is the **product and user documentation hub** for SecureHub. Use it when you need to understand what the system does, who uses which part, and what to click in what order.

**In the console:** open **Help** at the bottom of the sidebar (or go to `/console/help/`) for the full guides with navigation — same content as this folder, rendered in the app.

Technical setup remains in [README.md](../README.md) (root) and [backend/README.md](../backend/README.md).

---

## Start here

| If you are… | Read first | Then |
|-------------|------------|------|
| **New to SecureHub** | [system-overview.md](system-overview.md) | [feature-guide.md](feature-guide.md) |
| **Staff on `/console/`** | [user-guide-staff-console.md](user-guide-staff-console.md) | Role-specific sections in [feature-guide.md](feature-guide.md) |
| **Guarding / scheduling / HR** | [user-guide-guarding-ops.md](user-guide-guarding-ops.md) | [feature-guide.md](feature-guide.md) → Guarding |
| **Field guard (mobile app)** | [user-guide-guard-mobile.md](user-guide-guard-mobile.md) | [guard-mobile-api.md](guard-mobile-api.md) |
| **Alarm customer (mobile app)** | [user-guide-alarm-customer.md](user-guide-alarm-customer.md) | — |
| **Guarding client (reports portal)** | [user-guide-guarding-client.md](user-guide-guarding-client.md) | — |

---

## Guides (this plan)

| Document | Description |
|----------|-------------|
| [system-overview.md](system-overview.md) | Mental model: four access layers, entity chains, how modules connect |
| [feature-guide.md](feature-guide.md) | Feature catalog by module (console, API, public apply) |
| [user-guide-staff-console.md](user-guide-staff-console.md) | Operator console: roles, sidebar, common tasks |
| [user-guide-guarding-ops.md](user-guide-guarding-ops.md) | End-to-end guarding playbook and URL map |
| [user-guide-guard-mobile.md](user-guide-guard-mobile.md) | Field guard shift day |
| [user-guide-alarm-customer.md](user-guide-alarm-customer.md) | Alarm mobile customer |
| [user-guide-guarding-client.md](user-guide-guarding-client.md) | B2B guarding client portal |

---

## Existing technical docs

| Document | Description |
|----------|-------------|
| [operator-rbac.md](operator-rbac.md) | Console roles and permission codenames |
| [guard-mobile-api.md](guard-mobile-api.md) | Guard REST API reference |
| [emergency-addon-runbook.md](emergency-addon-runbook.md) | Emergency add-on billing and ops |
| [guard-monitoring-system-roadmap.md](guard-monitoring-system-roadmap.md) | Guard monitoring roadmap |
| [guard-monitoring-delivery-checklist.md](guard-monitoring-delivery-checklist.md) | Delivery checklist |

---

## Glossary

| Term | Meaning |
|------|---------|
| **Site** | A monitored location (alarm panel / Hik devices). May also have guarding posts. |
| **CustomerSiteAccess** | Links a mobile user to a site as owner, manager, or viewer (alarm app). |
| **GuardPost** | A guard position at a site (gate, lobby, patrol area). |
| **Shift** | Scheduled work block on a post (start/end, required headcount). |
| **ShiftAssignment** | One guard assigned to one shift (`assigned` → `accepted` → `clocked_in` → `clocked_out`). |
| **GuardApplicant** | Hiring pipeline record before becoming a guard. |
| **GuardProfile** | Employed guard; optional login `User` for mobile app. |
| **PostAssetKit** | Standard equipment list for a post (radios, keys, etc.). |
| **ShiftAssetManifest** | Custody record for assets issued/returned on an assignment. |
| **PatrolRoute / PatrolRound** | Defined patrol path and a scheduled instance guards must complete. |
| **CheckpointScan** | Proof a guard scanned a checkpoint during a round. |
| **FieldReport** | Guard-submitted incident or activity report from the field. |
| **DispatchTask** | Work item for a guard (from panic, alarm, or emergency). |
| **GuardPanicAlert** | SOS from a guard’s mobile app. |
| **EmergencyRequest** | Mobile emergency service request (separate from intruder alarms). |
| **AlarmEvent** | Intruder alarm event from Hik / panel integration. |
| **ClientPortalAccess** | B2B client user allowed to view guarding reports/patrols for a site. |
| **StaffOperatorProfile** | Console role for staff (`platform_admin`, `operations`, `guarding`, etc.). |
| **OperationsZone** | Map grouping for filtering sites on the global map. |
| **Subscription** | Billing record controlling customer mobile access when suspended. |

---

## Console base URL

Staff operator UI: **`/console/`** (login at `/console/login/`).

Public guard application: **`/apply/guard/`** (when enabled).

Guard mobile API base: **`/api/v1/guarding/me/`** (authenticated guard).

Guarding client portal: **`/console/client/guarding/`**.
