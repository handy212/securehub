# SecureHub feature guide

Capability catalog for the operator console (`/console/`), public apply, guard APIs, and client portal. For step-by-step tasks, see the [user guides](README.md).

**Permissions:** Each console section requires `console.view_*` or `console.manage_*`. See [operator-rbac.md](operator-rbac.md).

---

## Dashboard

| Item | Detail |
|------|--------|
| **URL** | `/console/` |
| **Permission** | `console.view_dashboard` |
| **Purpose** | Ops home: cross-module KPIs (sites, alarms, guarding SOS/dispatch, billing MRR). |
| **Key actions** | **Global sync** (`POST /console/sync/global/`) — refreshes Hik devices, alarm status, health for all sites (`console.global_sync`). |

**Related:** Sites, Guarding overview, Emergency.

---

## Global map and zones

### Client map

| Item | Detail |
|------|--------|
| **URL** | `/console/map/` |
| **Permission** | `console.view_sites` |
| **Purpose** | Geographic view of sites with alarm status, active emergencies, and on-duty guard positions. |
| **API** | `GET /console/map/guards/poll/` — guard GPS snapshot (`console.view_guarding`). |

Guarding **Live map** (`/console/guarding/live-map/`) redirects here with `?focus=guards`.

### Map zones

| Item | Detail |
|------|--------|
| **URL** | `/console/map/zones/` |
| **Permission** | `console.manage_sites` (create/update/delete) |
| **Purpose** | CRUD for `OperationsZone` — filter and group sites on the map. |
| **Objects** | Zone name, color, sort order, active flag. |

---

## Emergency

| Item | Detail |
|------|--------|
| **URL** | `/console/emergency/` |
| **Permission** | View: `console.view_emergency`; actions: `console.manage_emergency` |
| **Purpose** | Queue and lifecycle for **mobile emergency requests** (distinct from intruder `AlarmEvent`). |
| **Workflow** | Assign staff → acknowledge → dispatch → arrive → resolve / cancel |
| **Services** | `/console/emergency/services/` — emergency plans and site/account add-on subscriptions |

**Related:** Guarding dispatch (guards may receive `DispatchTask` from emergencies), [emergency-addon-runbook.md](emergency-addon-runbook.md).

---

## Guarding module

Base path: `/console/guarding/`. Sub-nav in all guarding pages.

| Page | URL | Permission | Purpose |
|------|-----|------------|---------|
| Overview | `/console/guarding/` | `view_guarding` | Daily KPIs: shifts, coverage, panic, dispatch, patrols, reports, assets |
| Analytics | `/console/guarding/analytics/` | `view_guarding` | Charts over configurable date range |
| Applicants | `/console/guarding/applicants/` | `manage_guarding` | Hiring pipeline, intake modal, PDF, hire action |
| Guards | `/console/guarding/guards/` | `manage_guarding` | Roster, credentials, compliance, contracts |
| Assets | `/console/guarding/assets/` | `view_guarding` / `manage_guarding` | Catalog, depots, stock, post kits, policies, open manifests |
| Posts | `/console/guarding/posts/` | `manage_guarding` | Guard posts, post orders, kits (subset) |
| Shifts | `/console/guarding/shifts/` | `manage_guarding` | Shifts, assignments, clock, welfare, **shift asset custody** |
| Patrols | `/console/guarding/patrols/` | `manage_guarding` | Routes, checkpoints, rounds, QR export, CSV proof |
| Reports | `/console/guarding/reports/` | `manage_guarding` | Field reports, review approve/reject, CSV export |
| Back office | `/console/guarding/back-office/` | `manage_guarding` | Timesheets, invoices, training, offboarding |
| Dispatch | `/console/guarding/dispatch/` | `manage_guarding` | Panic alerts, dispatch tasks, welfare queue; live poll API |

### Applicants

- **Objects:** `GuardApplicant`, documents, education, employment, references, profile.
- **Statuses:** `applied` → `screening` → `interview` → `background_check` → `offered` → `hired` | `rejected` | `withdrawn`.
- **Actions:** Create/edit in console; **Hire** (`POST .../applicants/<id>/hire/`) creates `GuardProfile` as **inactive**; download application PDF.
- **Public:** Same intake via `/apply/guard/` when enabled.

### Guards

- **Objects:** `GuardProfile`, `GuardCredential`, documents, training, equipment issues, offboarding checklist.
- **Statuses:** `active`, `suspended`, `inactive`, `terminated`.
- **Compliance:** Activation blocked until required credentials/training satisfied (`ensure_guard_compliance_ready`).

### Posts

- **Objects:** `GuardPost` (per site), `PostOrder` (standing instructions), optional post kits.
- **Fields:** Geofence radius, supervisor, required credentials JSON.

### Shifts and assignments

- **Objects:** `Shift` (`draft` → `published` → `in_progress` → `completed`), `ShiftAssignment`, `ClockEvent`, `WelfareCheck`.
- **Assignment flow:** `assigned` → `accepted` → `clocked_in` → `clocked_out` (also `declined`, `no_show`, `removed`).
- **Asset panel:** Build manifest from post kit, issue/return lines, close manifest, override enforcement.

### Assets (catalog and custody)

Tabs on `/console/guarding/assets/`:

| Tab | CRUD | Notes |
|-----|------|-------|
| **Catalog** | Types + serial units | Types: metadata JSON, condition-check flag; units: maintenance logs in edit modal |
| **Depots** | Depots | Site-scoped or central |
| **Stock** | Quantity stock per type+depot | Consumable types only |
| **Post kits** | Kits + lines | Default kit per post; inline add lines |
| **Policies** | Site or post enforcement | Advisory vs strict; clock-in/out rules |
| **Open manifests** | Read + full custody ops | Same actions as Shifts panel: issue, return, rebuild, add/edit/remove pending lines |

Manifest **create** also available at bottom of Open manifests tab and on **Shifts**.

### Patrols

- **Objects:** `Checkpoint`, `PatrolRoute`, `PatrolRouteCheckpoint`, `PatrolRound`, `CheckpointScan`.
- **Round statuses:** `scheduled` → `in_progress` → `completed` | `missed`.
- **Exports:** CSV proof; checkpoint QR SVG per checkpoint.

### Reports

- **Objects:** `FieldReport`, attachments, client acknowledgements.
- **Review:** Staff approve/reject; client portal can acknowledge if allowed.

### Dispatch

- **Objects:** `GuardPanicAlert`, `DispatchTask`, `WelfareCheck`.
- **Dispatch task states:** open → assigned → accepted → en_route → arrived → resolved (cancel available).
- **Poll:** `/console/guarding/dispatch/poll/` for live counts.

### Back office

- **Objects:** `GuardContract`, `GuardTimesheet`, `GuardInvoice`, invoice lines.
- **Exports:** Timesheet CSV.

---

## Sites

| Item | Detail |
|------|--------|
| **URL** | `/console/sites/` → `/console/sites/<uuid>/` (site console) |
| **Permission** | View: `view_sites`; provision/edit/arm: `manage_sites` |
| **Purpose** | Site directory, Hik provisioning, panels, zones, arm/disarm, customer handover, `CustomerSiteAccess`. |
| **Key actions** | Provision site, register panel, Hik add/remove device, onboard client, per-subsystem arm/disarm/clear, edit metadata, delete site |
| **Events** | Event pictures JSON for alarm media |

**Related:** Map, Billing (subscription per site), Guarding posts (same `Site`).

---

## Billing

| Item | Detail |
|------|--------|
| **URL** | `/console/subscriptions/` |
| **Permission** | View: `view_billing`; manage: `manage_billing` |
| **Purpose** | Packages, subscriptions, payments, suspend/cancel/reactivate; emergency add-on MRR rollup. |
| **Impact** | Suspended subscription can block **owner** mobile alarm access (`IsSubscriptionActive`). |

---

## Accounts

### Staff users

| Item | Detail |
|------|--------|
| **URL** | `/console/users/` |
| **Permission** | `console.manage_staff` (typically superuser / platform_admin) |
| **Purpose** | Create staff accounts, assign `StaffOperatorProfile.role`. |

### Customers and groups

| Item | Detail |
|------|--------|
| **URL** | `/console/customers/`, `/console/customers/groups/` |
| **Permission** | View/manage customers per role |
| **Purpose** | Mobile alarm app users; customer groups for broadcast targeting. |

---

## Messaging

| Item | Detail |
|------|--------|
| **URL** | `/console/broadcast/` |
| **Permission** | `console.manage_broadcast` |
| **Purpose** | Compose FCM push / in-app broadcasts to users or customer groups; resend, edit, delete sent messages. |

---

## Audit logs and settings

| Item | Detail |
|------|--------|
| **Audit logs** | `/console/logs/` — `view_logs` — paginated alarm/event timeline |
| **Settings** | `/console/settings/` — `manage_settings` — read-only platform config (Hik, Celery, FCM, DB) |

---

## Public guard apply

| Item | Detail |
|------|--------|
| **URL** | `/apply/guard/`, success `/apply/guard/success/<applicant_id>/` |
| **Auth** | None |
| **Purpose** | 4-step wizard; creates `GuardApplicant` with `source=public_web`. |
| **Gate** | `GUARD_PUBLIC_APPLY_ENABLED` — 404 when off |

---

## Guard REST API

| Prefix | Auth | Purpose |
|--------|------|---------|
| `/api/v1/guarding/` | Staff `IsAdminUser` | Full CRUD ViewSets: applicants, guards, shifts, patrol, dispatch, assets, etc. |
| `/api/v1/guarding/me/` | Authenticated + `GuardProfile` | Guard mobile: shifts, clock, patrol scan, reports, panic, welfare, dispatch, asset readiness |

Reference: [guard-mobile-api.md](guard-mobile-api.md).

**Note:** Staff API uses `IsAdminUser` (any `is_staff`), which is broader than per-page console RBAC.

---

## Guarding client portal

| Item | Detail |
|------|--------|
| **URL** | `/console/client/guarding/` |
| **Auth** | `ClientPortalAccess` (not staff RBAC) |
| **Purpose** | Read-only (per flags): approved reports, patrols, attendance, timesheets; acknowledge reports; CSV export |

Guide: [user-guide-guarding-client.md](user-guide-guarding-client.md).

---

## Alarm customer (mobile)

Not a console module. Access via `CustomerSiteAccess` on site APIs.

Guide: [user-guide-alarm-customer.md](user-guide-alarm-customer.md).

---

## Cross-module dependencies

| From | To | Why |
|------|-----|-----|
| Site | GuardPost, Shift | Guarding anchored on sites |
| Site | AlarmEvent, panels | Hik integration |
| Site | Subscription | Billing lockout for customers |
| PostAssetKit | ShiftAssetManifest | Built when manifest created |
| GuardingAssetPolicy | Clock in/out | Strict mode blocks until assets issued/returned |
| Alarm / Emergency | DispatchTask | `SiteGuardDispatchPolicy` + bridge |
| Applicant hire | GuardProfile inactive | Compliance before `active` |

---

## Maintainer notes

When adding a console route, update:

1. `apps/accounts/rbac.py` — `CONSOLE_ROUTE_PERMISSIONS`
2. `docs/feature-guide.md` — this file
3. Relevant [user guide](README.md) if workflow changes
