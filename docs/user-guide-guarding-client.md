# User guide: guarding client portal

For **B2B clients** (property managers, site owners) who need visibility into **guarding service delivery**—reports, patrols, attendance—not alarm panel control.

**URL:** `/console/client/guarding/`  
**Auth:** Standard login; access is granted by **`ClientPortalAccess`** rows (not staff operator roles).

---

## How this differs from other access

| Access type | Purpose | Entry |
|-------------|---------|--------|
| **CustomerSiteAccess** | Alarm mobile app — arm/disarm | Mobile app |
| **StaffOperatorProfile** | Run operations | `/console/` staff sidebar |
| **ClientPortalAccess** | Read guarding deliverables | `/console/client/guarding/` |

You may have both customer and client access as separate users, or one user with both link types—each is checked independently.

---

## How you get access

An operator (guarding or operations staff) creates:

1. A **user account** (may share email with other products).
2. **`ClientPortalAccess`** for each **site** you should see, with:
   - **Role:** `viewer`, `manager`, or `approver` (organizational semantics)
   - **Flags:**
     - `can_view_reports`
     - `can_view_patrols`
     - `can_view_attendance`
     - `can_acknowledge_reports`

Without at least one access row, `/console/client/guarding/` is unavailable.

---

## What you can do in the portal

| Feature | When enabled |
|---------|----------------|
| View **approved** field reports | `can_view_reports` |
| **Acknowledge** a report | `can_acknowledge_reports` |
| View patrol proof / rounds | `can_view_patrols` |
| View attendance / clock summary | `can_view_attendance` |
| Export reports CSV | `/console/client/guarding/reports.csv` |

Data is **read-only** except acknowledgements. You cannot schedule guards, edit shifts, or issue equipment.

---

## Typical workflow

1. Log in (same login page as staff, but you only see client guarding routes you are allowed).
2. Open **Client guarding** home — sites listed from your access rows.
3. Open a **report** → read details → **Acknowledge** if your contract requires sign-off.
4. Download **CSV** for monthly records if needed.

Staff must **approve** reports in `/console/guarding/reports/` before they appear for clients (unless product rules differ for your deployment).

---

## What you cannot see

| Hidden from portal | Visible to staff |
|--------------------|------------------|
| Applicant PII pipeline | Applicants |
| Guard HR, credentials, pay | Guards, back office |
| Open SOS / dispatch console | Dispatch |
| Asset manifests and depots | Assets |
| Unapproved draft reports | Reports (pending) |
| Alarm arm/disarm | Customer mobile app |

---

## Acknowledgements

Acknowledging a report records client sign-off (`POST /console/client/guarding/reports/<id>/acknowledge/`). Use this when your SLA requires documented receipt of incident or daily activity reports.

---

## Troubleshooting

| Problem | Resolution |
|---------|------------|
| Login works but guarding portal 403/redirect | No `ClientPortalAccess` — ask service provider |
| Empty reports list | Reports may be pending staff approval, or flag `can_view_reports` is false |
| Wrong site list | Operator must add/remove access rows per site |
| Need alarm control | Use **customer mobile app**, not this portal |

---

## See also

- [user-guide-guarding-ops.md](user-guide-guarding-ops.md) — what staff do before data reaches you
- [system-overview.md](system-overview.md) — four access layers
- [feature-guide.md](feature-guide.md) — Guarding client portal section
