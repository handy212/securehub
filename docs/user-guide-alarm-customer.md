# User guide: alarm customer (mobile app)

For **end customers** who monitor and control **intruder alarm systems** at one or more sites through the SecureHub mobile app. This is **not** the staff console (`/console/`) and **not** the guarding client portal.

Staff manage your access from **Customers** and **Sites** in the console.

---

## How you are set up

1. An operator creates your **user account** (`/console/customers/`).
2. You receive **`CustomerSiteAccess`** on each site:
   - **owner** — primary account; subscription status affects your access
   - **manager** — can manage users and often control alarms
   - **viewer** — read-only status; alarm control depends on flags
3. **`can_control_alarm`** on your access row determines whether you can arm, disarm, and clear alarms.

You log into the **mobile app**, not `/console/login/`.

---

## What you can do in the app

| Feature | Typical capability |
|---------|-------------------|
| View sites you are granted | List sites from access table |
| Live status | Partitions/zones armed state, zone health |
| Arm / disarm / stay arm | If role + `can_control_alarm` allow |
| Clear / cancel active alarm | When panel reports active alarm |
| Notifications | Push for alarm events (FCM) |
| Emergency request | Separate from intruder alarms — see emergency flow in app |

Exact screens depend on the Flutter app version; backend enforces permissions regardless of UI.

---

## Roles and permissions

| Role | Usually can |
|------|-------------|
| **owner** | Full site control; billing/subscription tied to account |
| **manager** | Invite/manage other users (per product rules); control alarms if flagged |
| **viewer** | See status; arm/disarm only if `can_control_alarm` is true |

Staff configure access on the **site console** → customer access section.

---

## Subscription lockout

If you are the **owner** and your site **subscription** is suspended or cancelled:

- Mobile APIs may return **403** via `IsSubscriptionActive`.
- You cannot use alarm features until billing is restored.

Managers/viewers on the same site may have different rules—check with your service provider.

---

## What you cannot do

| Not for customers | Who uses it |
|-------------------|-------------|
| `/console/` operator dashboard | Staff only |
| Hire guards, schedules, patrols | Guarding module / staff |
| View guard internal reports (unless also given **ClientPortalAccess**) | Guarding client portal |
| Register new sites without staff | Operations provisions sites |

---

## Relationship to guarding

Your site may also have **physical guards** (patrols, shifts). That operations layer does not appear in the alarm app unless:

- You are separately given **guarding client portal** access ([user-guide-guarding-client.md](user-guide-guarding-client.md)), or
- The mobile product combines views in a future release.

Intruder **alarms** and **emergency requests** are different event types; emergency may create dispatch activity guards respond to.

---

## Getting help

| Issue | Contact |
|-------|---------|
| Cannot see a site | Ask operator to add `CustomerSiteAccess` |
| Arm/disarm greyed out | Check role and `can_control_alarm`; panel may be offline |
| App says subscription inactive | Billing / account owner |
| False alarm | Use clear alarm; contact monitoring center per your contract |

---

## Technical reference

- Site access model: `CustomerSiteAccess` in `apps/sites/models.py`
- Permission classes: `apps/sites/permissions.py` (`HasSiteAccess`, `CanControlAlarm`, `IsSubscriptionActive`)
- Product architecture: [README.md](../README.md), [system-overview.md](system-overview.md)
