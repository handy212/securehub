#!/usr/bin/env python3
"""Phase 3: guarding page toolbars + scrollable data tables."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "backend/apps/dashboard/templates/dashboard"

GUARDING_HEADERS = [
    (
        '    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">\n'
        '        <div class="flex min-w-0 flex-1 items-start gap-4">',
        '    <div class="console-page-toolbar">\n        <div class="min-w-0 flex-1">',
    ),
    (
        '    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">\n'
        '        <div class="min-w-0 flex-1">',
        '    <div class="console-page-toolbar">\n        <div class="min-w-0 flex-1">',
    ),
    (
        '    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">\n'
        '        {% include "dashboard/partials/console/page_header.html"',
        '    <div class="console-page-toolbar">\n'
        '        {% include "dashboard/partials/console/page_header.html"',
    ),
    (
        'class="flex flex-shrink-0 flex-wrap justify-end gap-2"',
        'class="console-page-actions"',
    ),
]

DATA_TABLE_SCROLL_FILES = [
    "guarding/reports.html",
    "guarding/shifts.html",
    "guarding/guards.html",
    "guarding/posts.html",
    "guarding/applicants.html",
    "customers/list.html",
    "sites/directory.html",
    "ops/logs.html",
    "billing/subscriptions.html",
    "emergency/dispatch.html",
    "billing/packages.html",
    "customers/groups.html",
]


def main() -> None:
    changed: list[str] = []

    for path in sorted(TEMPLATES.glob("guarding/*.html")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in GUARDING_HEADERS:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(path.name)

    for name in DATA_TABLE_SCROLL_FILES:
        path = TEMPLATES / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        needle = 'data_table_start.html" with table_min_width_class='
        if needle not in text or "table_scrollable" in text:
            continue
        text = text.replace(
            'data_table_start.html" with table_min_width_class=',
            'data_table_start.html" with table_scrollable=True table_min_width_class=',
        )
        path.write_text(text, encoding="utf-8")
        changed.append(f"{name} (scroll)")

    print(f"Updated {len(changed)} files:")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
