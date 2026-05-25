#!/usr/bin/env python3
"""Phase 4: command center ops cards, panel headers, client guarding polish."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "backend/apps/dashboard/templates/dashboard"


def patch_guarding_overview() -> None:
    path = T / "guarding/overview.html"
    text = path.read_text(encoding="utf-8")

    text = re.sub(
        r"    \.guard-overview \.ops-panel \{[^}]+\}\s*"
        r"    \.guard-overview \.ops-panel:hover \{[^}]+\}\s*"
        r"    \.dark \.guard-overview \.ops-panel:hover \{[^}]+\}\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"    @media \(min-width: 1280px\) \{\s*"
        r"        \.guard-overview \.ops-sticky \{[^}]+\}\s*"
        r"    \}\s*",
        "",
        text,
        flags=re.DOTALL,
    )

    pairs = [
        ("ops-panel overflow-hidden console-table-card shadow-sm dark:border-slate-800 dark:bg-slate-900", "console-ops-card overflow-hidden"),
        ("ops-panel console-table-card p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900", "console-ops-card p-4"),
        ("ops-panel console-table-card shadow-sm dark:border-slate-800 dark:bg-slate-900", "console-ops-card"),
        ("ops-panel ops-sticky overflow-hidden console-table-card shadow-sm dark:border-slate-800 dark:bg-slate-900", "console-ops-card console-ops-sticky overflow-hidden"),
        ('class="mt-1 text-sm font-black text-slate-900 dark:text-slate-100"', 'class="console-panel-title mt-1"'),
        ('class="mt-0.5 text-sm font-black text-slate-900 dark:text-slate-100"', 'class="console-panel-title mt-0.5"'),
        ('class="truncate text-[11px] font-black text-slate-900 dark:text-slate-100"', 'class="console-row-title"'),
        ('class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-black text-slate-600 dark:bg-slate-800 dark:text-slate-300"', 'class="console-count-pill"'),
        ('class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-300"', 'class="console-count-pill text-slate-500"'),
        ('class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"', 'class="console-count-pill"'),
        ('class="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 dark:border-slate-800"', 'class="console-panel-header"'),
        ('class="console-label text-brand hover:text-red-700"', 'class="console-panel-link"'),
        ('class="text-2xl font-black tabular-nums text-slate-900 dark:text-slate-100"', 'class="console-stat-value text-2xl"'),
        ('class="text-3xl font-black tabular-nums text-slate-900 dark:text-slate-100"', 'class="console-stat-value text-3xl"'),
        ('class="text-base font-black tabular-nums text-slate-900 dark:text-slate-100"', 'class="console-stat-value text-base"'),
        ('class="text-lg font-black tabular-nums text-slate-900 dark:text-slate-100"', 'class="console-stat-value"'),
        ('class="text-lg font-black tabular-nums text-amber-600"', 'class="console-stat-value text-amber-600"'),
        ('class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black text-slate-700 dark:bg-slate-800 dark:text-slate-200"', 'class="console-count-chip"'),
        ('class="rounded bg-red-50 px-2 py-1 text-[10px] font-black text-red-600 dark:bg-red-950/40 dark:text-red-300"', 'class="rounded bg-red-50 px-2 py-1 text-[11px] font-medium text-red-600 dark:bg-red-950/40 dark:text-red-300"'),
        ('class="rounded bg-amber-50 px-2 py-1 text-[10px] font-black text-amber-600 dark:bg-amber-950/40 dark:text-amber-300"', 'class="rounded bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-600 dark:bg-amber-950/40 dark:text-amber-300"'),
        ('class="rounded bg-emerald-50 px-2 py-1 text-[10px] font-black text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-300"', 'class="rounded bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-300"'),
        ('<motion class="console-table-wrap">\n            <table class="console-table min-w-[780px]">', '<div class="console-table-wrap console-table-wrap--scroll">\n            <table class="console-table min-w-[780px]">'),
    ]
    for old, new in pairs:
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")
    print("  guarding_overview.html")


def patch_client_guarding() -> None:
    path = T / "client_guarding.html"
    text = path.read_text(encoding="utf-8")
    pairs = [
        (
            """        <header class="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <p class="console-label text-brand">SecureHub Guarding</p>
                <h1 class="text-xl font-black text-slate-950">Client Activity</h1>
            </div>
            <div class="flex flex-wrap gap-2 console-label">""",
            """        <header class="console-page-toolbar">
            <div>
                <p class="console-label text-brand">SecureHub Guarding</p>
                <h1 class="console-page-title">Client activity</h1>
                <p class="console-page-subtitle">Approved reports, patrol proof, and attendance for your sites</p>
            </div>
            <div class="console-page-actions">""",
        ),
        (
            '<div class="console-table-card p-4"><p class="console-label text-slate-400">Sites</p><p class="mt-1 text-2xl font-black text-slate-950 dark:text-slate-100">',
            '<div class="console-stat-card"><p class="console-stat-label">Sites</p><p class="mt-1 console-stat-value text-2xl">',
        ),
        (
            '<div class="console-table-card p-4"><p class="console-label text-slate-400">Approved reports</p><p class="mt-1 text-2xl font-black text-slate-950 dark:text-slate-100">',
            '<div class="console-stat-card"><p class="console-stat-label">Approved reports</p><p class="mt-1 console-stat-value text-2xl">',
        ),
        (
            '<div class="console-table-card p-4"><p class="console-label text-slate-400">Patrol rounds</p><p class="mt-1 text-2xl font-black text-slate-950 dark:text-slate-100">',
            '<div class="console-stat-card"><p class="console-stat-label">Patrol rounds</p><p class="mt-1 console-stat-value text-2xl">',
        ),
        (
            '<div class="console-table-card p-4"><p class="console-label text-slate-400">Attendance rows</p><p class="mt-1 text-2xl font-black text-slate-950 dark:text-slate-100">',
            '<div class="console-stat-card"><p class="console-stat-label">Attendance rows</p><p class="mt-1 console-stat-value text-2xl">',
        ),
        ('<div class="console-table-wrap">', '<div class="console-table-wrap console-table-wrap--scroll">'),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("  client_guarding.html")


def patch_guarding_backoffice() -> None:
    path = T / "guarding/backoffice.html"
    text = path.read_text(encoding="utf-8")
    new_text = text.replace(
        '<div class="console-table-wrap">',
        '<div class="console-table-wrap console-table-wrap--scroll">',
    )
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("  guarding_backoffice.html")


def main() -> None:
    print("Phase 4 patches:")
    patch_guarding_overview()
    patch_client_guarding()
    patch_guarding_backoffice()


if __name__ == "__main__":
    main()
