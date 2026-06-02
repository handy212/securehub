#!/usr/bin/env python3
"""Reorganize dashboard templates into domain folders and grouped partials."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "backend/apps/dashboard/templates/dashboard"

# (old_path_relative_to_T, new_path_relative_to_T)
FILE_MOVES: list[tuple[str, str]] = [
    # Auth
    ("login.html", "auth/login.html"),
    ("password_reset_base.html", "auth/password_reset_base.html"),
    ("password_reset_form.html", "auth/password_reset_form.html"),
    ("password_reset_done.html", "auth/password_reset_done.html"),
    ("password_reset_confirm.html", "auth/password_reset_confirm.html"),
    ("password_reset_complete.html", "auth/password_reset_complete.html"),
    ("password_reset_email.txt", "auth/password_reset_email.txt"),
    ("password_reset_subject.txt", "auth/password_reset_subject.txt"),
    # Ops
    ("home.html", "ops/home.html"),
    ("settings.html", "ops/settings.html"),
    ("users.html", "ops/users.html"),
    ("broadcast.html", "ops/broadcast.html"),
    ("logs.html", "ops/logs.html"),
    ("site_map.html", "ops/site_map.html"),
    # Sites
    ("sites.html", "sites/directory.html"),
    ("site_console.html", "sites/console.html"),
    ("site_update.html", "sites/update.html"),
    ("onboard.html", "sites/onboard.html"),
    # Customers
    ("customers.html", "customers/list.html"),
    ("groups.html", "customers/groups.html"),
    # Billing
    ("subscriptions.html", "billing/subscriptions.html"),
    ("packages.html", "billing/packages.html"),
    # Emergency
    ("emergency.html", "emergency/dispatch.html"),
    ("emergency_services.html", "emergency/services.html"),
    # Guarding
    ("guarding_nav.html", "guarding/_nav.html"),
    ("guarding_overview.html", "guarding/overview.html"),
    ("guarding_analytics.html", "guarding/analytics.html"),
    ("guarding_applicants.html", "guarding/applicants.html"),
    ("guarding_guards.html", "guarding/guards.html"),
    ("guarding_posts.html", "guarding/posts.html"),
    ("guarding_shifts.html", "guarding/shifts.html"),
    ("guarding_patrols.html", "guarding/patrols.html"),
    ("guarding_reports.html", "guarding/reports.html"),
    ("guarding_backoffice.html", "guarding/backoffice.html"),
    ("guarding_live_map.html", "guarding/live_map.html"),
    ("guarding_dispatch.html", "guarding/dispatch.html"),
    ("client_guarding.html", "guarding/client.html"),
    # Partials → console/
    ("partials/console/modal_start.html", "partials/console/modal_start.html"),
    ("partials/console_modal_inner_end.html", "partials/console/modal_end.html"),
    ("partials/data_table_start.html", "partials/console/data_table_start.html"),
    ("partials/data_table_end.html", "partials/console/data_table_end.html"),
    ("partials/breadcrumbs.html", "partials/console/breadcrumbs.html"),
    ("partials/page_title_bar.html", "partials/console/page_title_bar.html"),
    ("partials/console/page_header.html", "partials/console/page_header.html"),
    ("partials/panel_section_header.html", "partials/console/panel_section_header.html"),
    # Partials → domain
    ("partials/site/breadcrumbs.html", "partials/site/breadcrumbs.html"),
    ("partials/emergency_service_fields.html", "partials/emergency/service_fields.html"),
]

# Old Django template_name / include path → new path
PATH_REPLACEMENTS: list[tuple[str, str]] = [
    ('"dashboard/partials/console/modal_start.html"', '"dashboard/partials/console/modal_start.html"'),
    ("'dashboard/partials/console/modal_start.html'", "'dashboard/partials/console/modal_start.html'"),
    ('"dashboard/partials/console/modal_end.html"', '"dashboard/partials/console/modal_end.html"'),
    ("'dashboard/partials/console/modal_end.html'", "'dashboard/partials/console/modal_end.html'"),
    ('"dashboard/partials/console/data_table_start.html"', '"dashboard/partials/console/data_table_start.html"'),
    ("'dashboard/partials/console/data_table_start.html'", "'dashboard/partials/console/data_table_start.html'"),
    ('"dashboard/partials/console/data_table_end.html"', '"dashboard/partials/console/data_table_end.html"'),
    ("'dashboard/partials/console/data_table_end.html'", "'dashboard/partials/console/data_table_end.html'"),
    ('"dashboard/partials/console/breadcrumbs.html"', '"dashboard/partials/console/breadcrumbs.html"'),
    ("'dashboard/partials/console/breadcrumbs.html'", "'dashboard/partials/console/breadcrumbs.html'"),
    ('"dashboard/partials/console/page_title_bar.html"', '"dashboard/partials/console/page_title_bar.html"'),
    ("'dashboard/partials/console/page_title_bar.html'", "'dashboard/partials/console/page_title_bar.html'"),
    ('"dashboard/partials/console/page_header.html"', '"dashboard/partials/console/page_header.html"'),
    ("'dashboard/partials/console/page_header.html'", "'dashboard/partials/console/page_header.html'"),
    ('"dashboard/partials/console/panel_section_header.html"', '"dashboard/partials/console/panel_section_header.html"'),
    ("'dashboard/partials/console/panel_section_header.html'", "'dashboard/partials/console/panel_section_header.html'"),
    ('"dashboard/partials/site/breadcrumbs.html"', '"dashboard/partials/site/breadcrumbs.html"'),
    ("'dashboard/partials/site/breadcrumbs.html'", "'dashboard/partials/site/breadcrumbs.html'"),
    ('"dashboard/partials/emergency/service_fields.html"', '"dashboard/partials/emergency/service_fields.html"'),
    ("'dashboard/partials/emergency/service_fields.html'", "'dashboard/partials/emergency/service_fields.html'"),
    ('"dashboard/guarding/_nav.html"', '"dashboard/guarding/_nav.html"'),
    ("'dashboard/guarding/_nav.html'", "'dashboard/guarding/_nav.html'"),
    ('{% include "dashboard/guarding/_nav.html" %}', '{% include "dashboard/guarding/_nav.html" %}'),
    ('extends "dashboard/auth/password_reset_base.html"', 'extends "dashboard/auth/password_reset_base.html"'),
    ("extends 'dashboard/auth/password_reset_base.html'", "extends 'dashboard/auth/password_reset_base.html'"),
    ('template_name="dashboard/auth/login.html"', 'template_name="dashboard/auth/login.html"'),
    ('template_name="dashboard/ops/home.html"', 'template_name="dashboard/ops/home.html"'),
    ('template_name="dashboard/ops/settings.html"', 'template_name="dashboard/ops/settings.html"'),
    ('template_name="dashboard/ops/users.html"', 'template_name="dashboard/ops/users.html"'),
    ('template_name="dashboard/ops/broadcast.html"', 'template_name="dashboard/ops/broadcast.html"'),
    ('template_name="dashboard/ops/logs.html"', 'template_name="dashboard/ops/logs.html"'),
    ('template_name="dashboard/ops/site_map.html"', 'template_name="dashboard/ops/site_map.html"'),
    ('template_name="dashboard/sites/directory.html"', 'template_name="dashboard/sites/directory.html"'),
    ('template_name="dashboard/sites/console.html"', 'template_name="dashboard/sites/console.html"'),
    ('template_name="dashboard/sites/update.html"', 'template_name="dashboard/sites/update.html"'),
    ('template_name="dashboard/sites/onboard.html"', 'template_name="dashboard/sites/onboard.html"'),
    ('template_name="dashboard/customers/list.html"', 'template_name="dashboard/customers/list.html"'),
    ('template_name="dashboard/customers/groups.html"', 'template_name="dashboard/customers/groups.html"'),
    ('template_name="dashboard/billing/subscriptions.html"', 'template_name="dashboard/billing/subscriptions.html"'),
    ('template_name="dashboard/billing/packages.html"', 'template_name="dashboard/billing/packages.html"'),
    ('template_name="dashboard/emergency/dispatch.html"', 'template_name="dashboard/emergency/dispatch.html"'),
    ('template_name="dashboard/emergency/services.html"', 'template_name="dashboard/emergency/services.html"'),
    ('template_name="dashboard/guarding/overview.html"', 'template_name="dashboard/guarding/overview.html"'),
    ('template_name="dashboard/guarding/analytics.html"', 'template_name="dashboard/guarding/analytics.html"'),
    ('template_name="dashboard/guarding/applicants.html"', 'template_name="dashboard/guarding/applicants.html"'),
    ('template_name="dashboard/guarding/guards.html"', 'template_name="dashboard/guarding/guards.html"'),
    ('template_name="dashboard/guarding/posts.html"', 'template_name="dashboard/guarding/posts.html"'),
    ('template_name="dashboard/guarding/shifts.html"', 'template_name="dashboard/guarding/shifts.html"'),
    ('template_name="dashboard/guarding/patrols.html"', 'template_name="dashboard/guarding/patrols.html"'),
    ('template_name="dashboard/guarding/reports.html"', 'template_name="dashboard/guarding/reports.html"'),
    ('template_name="dashboard/guarding/backoffice.html"', 'template_name="dashboard/guarding/backoffice.html"'),
    ('template_name="dashboard/guarding/live_map.html"', 'template_name="dashboard/guarding/live_map.html"'),
    ('template_name="dashboard/guarding/dispatch.html"', 'template_name="dashboard/guarding/dispatch.html"'),
    ('template_name="dashboard/guarding/client.html"', 'template_name="dashboard/guarding/client.html"'),
    ('template_name="dashboard/auth/password_reset_form.html"', 'template_name="dashboard/auth/password_reset_form.html"'),
    ('template_name="dashboard/auth/password_reset_done.html"', 'template_name="dashboard/auth/password_reset_done.html"'),
    ('template_name="dashboard/auth/password_reset_confirm.html"', 'template_name="dashboard/auth/password_reset_confirm.html"'),
    ('template_name="dashboard/auth/password_reset_complete.html"', 'template_name="dashboard/auth/password_reset_complete.html"'),
    ('email_template_name="dashboard/auth/password_reset_email.txt"', 'email_template_name="dashboard/auth/password_reset_email.txt"'),
    ('subject_template_name="dashboard/auth/password_reset_subject.txt"', 'subject_template_name="dashboard/auth/password_reset_subject.txt"'),
]

SCRIPT_PATH_UPDATES: list[tuple[str, str]] = [
    ("templates/dashboard/sites/console.html", "templates/dashboard/sites/console.html"),
    ("templates/dashboard/guarding/", "templates/dashboard/guarding/"),
    ("partials/console/modal_start.html", "partials/console/modal_start.html"),
    ("partials/console/page_header.html", "partials/console/page_header.html"),
    ("partials/site/breadcrumbs.html", "partials/site/breadcrumbs.html"),
]

SCAN_DIRS = [
    ROOT / "backend/apps/dashboard",
    ROOT / "backend/apps/accounts",
    ROOT / "scripts",
]


def move_files() -> None:
    for old_rel, new_rel in FILE_MOVES:
        src = T / old_rel
        dst = T / new_rel
        if not src.exists():
            if dst.exists():
                continue
            raise FileNotFoundError(f"Missing source: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        print(f"  moved {old_rel} → {new_rel}")


def patch_text(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in PATH_REPLACEMENTS:
        text = text.replace(old, new)
    if path.suffix == ".py" and "scripts/" in str(path):
        for old, new in SCRIPT_PATH_UPDATES:
            text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def remove_obsolete() -> None:
    for name in ("partials/modal_shell_start.html", "partials/modal_shell_end.html"):
        path = T / name
        if path.exists():
            path.unlink()
            print(f"  removed obsolete {name}")


def main() -> None:
    print("Moving template files…")
    move_files()
    remove_obsolete()

    print("Patching references…")
    changed = 0
    for base in SCAN_DIRS:
        for path in base.rglob("*"):
            if path.suffix not in {".html", ".py", ".txt", ".md"}:
                continue
            if patch_text(path):
                changed += 1
                print(f"  patched {path.relative_to(ROOT)}")

    print(f"Done. Patched {changed} files.")


if __name__ == "__main__":
    main()
