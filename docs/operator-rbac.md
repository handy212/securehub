# Operator console RBAC

SecureHub uses three separate permission layers:

| Layer | Model | Users | Purpose |
|-------|--------|-------|---------|
| **Operator console** | `StaffOperatorProfile` | `is_staff` | Dashboard sections (sites, guarding, billing, …) |
| **Mobile / alarm customer** | `CustomerSiteAccess` | Mobile app users | Per-site owner / manager / viewer + `can_control_alarm` |
| **Guarding client portal** | `ClientPortalAccess` | External clients | Per-site viewer / manager / approver + report flags |

Django `is_superuser` still bypasses all console checks. `is_staff` is required to sign in to `/console/`.

## Operator roles

| Role | Typical use |
|------|-------------|
| `platform_admin` | Full console (assigned automatically to superusers) |
| `operations` | Sites, customers, emergency, sync, broadcast |
| `guarding` | Guarding module (read + manage) |
| `dispatcher` | Emergency + guarding dispatch / live map |
| `billing` | Subscriptions and payments |
| `support` | Customers, emergency (view), logs, messaging |
| `auditor` | Read-only across allowed modules |

Permissions are defined in `apps/accounts/rbac.py` (`Perm` + `CONSOLE_ROUTE_PERMISSIONS`).
For the full cross-product matrix, see [access-control-matrix.md](access-control-matrix.md).

## Managing staff

Superusers and platform administrators (`console.manage_staff`) can create staff users and assign a role on **Staff Users** (`/console/users/`).

After deploy, run:

```bash
python manage.py migrate accounts
```

Existing staff users receive profiles via data migration `0006_populate_staff_operator_profiles`.

## Code hooks

- Check permission: `user_has_console_permission(user, Perm.VIEW_SITES)`
- View mixin: `StaffRequiredMixin` (uses route map) or `required_console_permission = Perm.MANAGE_SITES`
- Templates: `{% if console_perm.VIEW_BILLING in console_permissions %}`
