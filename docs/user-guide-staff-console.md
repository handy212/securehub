# User guide: staff operator console

For anyone who signs in at **`/console/login/`** with a staff account (`is_staff=true`).

Overview: [system-overview.md](system-overview.md) · Features: [feature-guide.md](feature-guide.md) · Roles detail: [operator-rbac.md](operator-rbac.md)

---

## Before you start

1. You need a **staff account** created by an administrator (`/console/users/`).
2. Your account must have **`console.access`** via an assigned **operator role** on `StaffOperatorProfile`.
3. The sidebar only shows modules your role allows. If a link is missing, ask for a role change—not a bug.

Superusers see everything and bypass role checks.

---

## Role cheat sheet

| Role | Start here | You can usually… | You typically cannot… |
|------|------------|------------------|------------------------|
| **platform_admin** | Any module | Full console including staff users and settings | — |
| **operations** | Dashboard, Sites, Emergency | Manage sites, emergency, customers, broadcast; global sync | Guarding writes, billing writes, staff users |
| **guarding** | `/console/guarding/` | Read most areas; **full guarding** create/edit | Manage sites, emergency actions, billing |
| **dispatcher** | Emergency + Guarding dispatch | Emergency lifecycle; guarding dispatch/panic; view sites | Billing, customers, broadcast, site provisioning |
| **billing** | `/console/subscriptions/` | Subscriptions, packages, payments | Guarding, emergency manage, staff |
| **support** | Customers, Broadcast | Customer CRUD, messaging; view emergency | Guarding, billing manage, sites manage |
| **auditor** | Logs, read-only modules | View dashboard, sites, guarding, billing, logs | Any create/update/delete |

If your role is missing from the table, you may only have login access—contact an admin.

---

## Sidebar tour

| Menu item | URL | Typical tasks |
|-----------|-----|----------------|
| Dashboard | `/console/` | KPIs, global Hik sync |
| Global Map | `/console/map/` | Site + guard positions |
| Map zones | `/console/map/zones/` | Organize sites on map |
| Emergency | `/console/emergency/` | Mobile emergency queue |
| Guarding | `/console/guarding/` | Workforce and field ops (sub-pages below) |
| Sites | `/console/sites/` | Alarm sites, panels, handover |
| Audit logs | `/console/logs/` | Event history |
| Billing | `/console/subscriptions/` | Subscriptions |
| Staff users | `/console/users/` | Staff CRUD (restricted) |
| Customers | `/console/customers/` | Mobile users |
| Messaging | `/console/broadcast/` | Push broadcasts |
| Platform settings | `/console/settings/` | Environment readout |
| **Help** (bottom of sidebar) | `/console/help/` | Product guides, RBAC reference, API docs |

**Guarding sub-pages** (tabs or nav inside guarding):

| Page | URL |
|------|-----|
| Overview | `/console/guarding/` |
| Applicants | `/console/guarding/applicants/` |
| Guards | `/console/guarding/guards/` |
| Assets | `/console/guarding/assets/` |
| Posts | `/console/guarding/posts/` |
| Shifts | `/console/guarding/shifts/` |
| Patrols | `/console/guarding/patrols/` |
| Reports | `/console/guarding/reports/` |
| Back office | `/console/guarding/back-office/` |
| Dispatch | `/console/guarding/dispatch/` |
| Analytics | `/console/guarding/analytics/` |

Deep guarding workflows: [user-guide-guarding-ops.md](user-guide-guarding-ops.md).

---

## Task recipes

### Onboard a new alarm site and hand to a customer

**Role:** operations or platform_admin (`manage_sites`).

1. Go to **Sites** → **Provision site** (or use Hik-linked flow if configured).
2. Open the **site console** (`/console/sites/<id>/`).
3. Register panel / add Hik devices as needed.
4. Run **sync** or wait for events to confirm connectivity.
5. **Onboard client** — create or link customer and `CustomerSiteAccess` (owner/manager/viewer, `can_control_alarm` if they should arm/disarm).
6. Ensure a **subscription** exists in Billing if the customer must use the mobile app (suspended subs block owners).

### Respond to an emergency request

**Role:** dispatcher or operations (`manage_emergency`).

1. Open **Emergency** `/console/emergency/`.
2. Select the open request.
3. **Assign** a staff member if required.
4. Progress: **acknowledge** → **dispatch** → **arrive** → **resolve** (or **cancel** if invalid).
5. If guards must respond, check **Guarding → Dispatch** for linked `DispatchTask` (auto-created per site policy).

See [emergency-addon-runbook.md](emergency-addon-runbook.md) for add-on billing.

### Run global sync after Hik changes

**Role:** operations (`global_sync`).

1. **Dashboard** `/console/`.
2. Use **Global sync** (refreshes devices and alarm status for all sites).
3. Verify on **Global Map** or the site console that status looks correct.

### Create a staff user and assign a role

**Role:** platform_admin (`manage_staff`).

1. **Staff users** `/console/users/`.
2. **Create user** — set username, email, `is_staff=true`.
3. Assign **operator role** (e.g. `guarding`, `dispatcher`).
4. Ask the user to log in at `/console/login/` and confirm sidebar matches expectations.

### Send a broadcast to a customer group

**Role:** operations or support (`manage_broadcast`).

1. **Messaging** `/console/broadcast/`.
2. Compose title/body, choose targets (users or **customer group**).
3. Send; use resend/edit/delete on past messages if needed.

### Review alarm history for one site

**Role:** auditor or anyone with `view_logs` / site access.

1. **Audit logs** `/console/logs/` — filter by site, or
2. **Site console** → events section for that site.

---

## When you are redirected to home

The console redirects to `/console/` with an error if you open a URL your role cannot access. Fix: use the sidebar, or request the correct role from an admin.

---

## Related guides

| Persona | Guide |
|---------|--------|
| Guarding scheduler / HR | [user-guide-guarding-ops.md](user-guide-guarding-ops.md) |
| Field guard (mobile) | [user-guide-guard-mobile.md](user-guide-guard-mobile.md) |
| B2B guarding client | [user-guide-guarding-client.md](user-guide-guarding-client.md) |
