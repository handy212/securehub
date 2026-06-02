#!/usr/bin/env python3
"""Phase 3 template patches (headers, scroll wraps, typography)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "backend/apps/dashboard/templates/dashboard"


def patch(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def patch_site_console() -> None:
    path = T / "sites/console.html"
    text = path.read_text(encoding="utf-8")
    nav_re = re.compile(
        r"<!-- Breadcrumbs -->\s*"
        r'<nav class="flex items-center gap-2 console-meta mb-3">.*?</nav>\s*'
        r'<div class="flex flex-col gap-3 border-b border-slate-200 pb-3 lg:flex-row lg:items-center lg:justify-between">',
        re.DOTALL,
    )
    replacement = (
        '{% include "dashboard/partials/site/breadcrumbs.html" with site_name=site.name site_pk=site.pk %}\n'
        '        <div class="console-page-toolbar">'
    )
    new_text, n = nav_re.subn(replacement, text, count=1)
    if n:
        new_text = new_text.replace(
            '<div class="flex flex-wrap items-center justify-between gap-2 flex-shrink-0 sm:justify-end"',
            '<div class="console-page-actions flex-wrap items-center justify-between gap-2 flex-shrink-0 sm:justify-end"',
            1,
        )
        new_text = new_text.replace(
            '<h4 class="text-sm font-black text-white uppercase italic tracking-wider">Lockdown Active</h4>',
            '<h4 class="text-sm font-semibold text-white">Lockdown active</h4>',
        )
        new_text = new_text.replace(
            '<h3 class="text-lg font-black text-slate-900 uppercase">Initiate Lockdown?</h3>',
            '<h3 class="text-lg font-semibold text-slate-900">Initiate lockdown?</h3>',
        )
        new_text = new_text.replace(
            '<h3 class="text-sm font-black text-slate-900">Trigger Panic</h3>',
            '<h3 class="text-sm font-semibold text-slate-900">Trigger panic</h3>',
        )
        path.write_text(new_text, encoding="utf-8")
        print("  site_console.html")


def patch_site_update() -> None:
    path = T / "site_update.html"
    text = path.read_text(encoding="utf-8")
    nav_re = re.compile(
        r'<nav class="flex items-center gap-2 console-meta">.*?</nav>\s*'
        r'<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">',
        re.DOTALL,
    )
    repl = (
        '{% include "dashboard/partials/site/breadcrumbs.html" with site_name=site.name site_pk=site.pk tail_label="Edit site" %}\n'
        '        <div class="console-page-toolbar">'
    )
    new_text, n = nav_re.subn(repl, text, count=1)
    if n:
        new_text = new_text.replace(
            '<h1 class="text-2xl font-black tracking-tight text-slate-900">{{ site.name }}</h1>',
            '<h1 class="console-page-title">{{ site.name }}</h1>',
            1,
        )
        path.write_text(new_text, encoding="utf-8")
        print("  site_update.html")


def patch_onboard() -> None:
    path = T / "onboard.html"
    text = path.read_text(encoding="utf-8")
    nav_re = re.compile(
        r'<!-- Breadcrumb -->\s*<nav class="flex items-center gap-2 console-label text-slate-400">.*?</nav>\s*'
        r'<!-- Page header -->\s*<div class="flex items-center justify-between border-b border-slate-200 pb-3">',
        re.DOTALL,
    )
    repl = (
        '{% include "dashboard/partials/site/breadcrumbs.html" with site_name=site.name site_pk=site.pk tail_label="Access" %}\n'
        '    <div class="console-page-toolbar">'
    )
    new_text, n = nav_re.subn(repl, text, count=1)
    if n:
        new_text = new_text.replace(
            '<h1 class="text-sm font-black tracking-tight text-slate-900 uppercase">',
            '<h1 class="console-page-title">',
            1,
        )
        path.write_text(new_text, encoding="utf-8")
        print("  onboard.html")


def patch_emergency_services() -> None:
    path = T / "emergency_services.html"
    old = """    <div class="flex flex-col gap-3 border-b border-slate-200 pb-3 lg:flex-row lg:items-center lg:justify-between">
        <motion>
            <h1 class="text-base font-black text-slate-900">Emergency Add-ons</h1>
        </div>
        <a href="{% url 'dashboard:emergency' %}" class="btn-console-secondary !min-h-0 py-2 text-[10px] hover:border-red-200 hover:text-red-600">Dispatch Queue</a>
    </div>"""
    new = """    {% include "dashboard/partials/console/breadcrumbs.html" with breadcrumb_parent_url=emergency_url breadcrumb_parent_label="Emergency" breadcrumb_current="Add-ons" %}
    <div class="console-page-toolbar">
        {% url 'dashboard:emergency' as emergency_url %}
        {% include "dashboard/partials/console/page_title_bar.html" with page_title="Emergency add-ons" %}
        <div class="console-page-actions">
            <a href="{% url 'dashboard:emergency' %}" class="btn-console-secondary hover:border-red-200 hover:text-red-600">Dispatch queue</a>
        </div>
    </motion>"""
    # Fix order - url tag must come before include
    new = """    {% url 'dashboard:emergency' as emergency_url %}
    {% include "dashboard/partials/console/breadcrumbs.html" with breadcrumb_parent_url=emergency_url breadcrumb_parent_label="Emergency" breadcrumb_current="Add-ons" %}
    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_title_bar.html" with page_title="Emergency add-ons" %}
        <div class="console-page-actions">
            <a href="{% url 'dashboard:emergency' %}" class="btn-console-secondary hover:border-red-200 hover:text-red-600">Dispatch queue</a>
        </div>
    </div>"""
    old = """    <div class="flex flex-col gap-3 border-b border-slate-200 pb-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
            <h1 class="text-base font-black text-slate-900">Emergency Add-ons</h1>
        </div>
        <a href="{% url 'dashboard:emergency' %}" class="btn-console-secondary !min-h-0 py-2 text-[10px] hover:border-red-200 hover:text-red-600">Dispatch Queue</a>
    </div>"""
    if patch(path, old, new):
        print("  emergency_services.html")


def patch_guards() -> None:
  # guarding overview h1
    path = T / "guarding/overview.html"
    text = path.read_text(encoding="utf-8")
    text2 = text.replace(
        '<h1 class="truncate text-lg font-black tracking-tight text-slate-900 dark:text-slate-100">Command Center</h1>',
        '<h1 class="console-page-title truncate">Command center</h1>',
    )
    text2 = text2.replace(
        '<p class="mt-0.5 truncate console-label text-slate-400 dark:text-slate-500">Coverage, dispatch, welfare, patrols, and field reports</p>',
        '<p class="console-page-subtitle mt-0.5 truncate">Coverage, dispatch, welfare, patrols, and field reports</p>',
    )
    if text2 != text:
        path.write_text(text2, encoding="utf-8")
        print("  guarding_overview.html")

    path = T / "guarding/live_map.html"
    old = """    <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
            <h1 class="text-lg font-black text-slate-900 dark:text-slate-100">Live guard positions</h1>
            <p class="console-label text-slate-400">Clocked-in guards · refreshes on load</p>
        </div>
        <div class="flex gap-2 console-label">"""
    new = """    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Live guard positions" page_subtitle="Clocked-in guards · refreshes on load" %}
        <div class="console-page-actions console-label">"""
    if patch(path, old, new):
        print("  guarding_live_map.html")

    path = T / "guarding/analytics.html"
    old = """<motion class="space-y-4">
    <form method="get" """
    new = """<div class="space-y-4">
    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Guarding analytics" page_subtitle="KPIs for the selected period" %}
    </div>
    <form method="get" """
    # fix motion typo
    old = """<div class="space-y-4">
    <form method="get" """
    new = """<div class="space-y-4">
    <motion class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Guarding analytics" page_subtitle="KPIs for the selected period" %}
    </div>
    <form method="get" """
    old = """<div class="space-y-4">
    <form method="get" """
    new = """<div class="space-y-4">
    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Guarding analytics" page_subtitle="KPIs for the selected period" %}
    </div>
    <form method="get" """
    if patch(path, old, new):
        print("  guarding_analytics.html")


def add_scroll_wraps() -> None:
    files = [
        "sites.html", "customers.html", "groups.html", "packages.html",
        "logs.html", "subscriptions.html", "emergency.html",
    ]
    for name in files:
        path = T / name
        text = path.read_text(encoding="utf-8")
        new_text = text.replace(
            '<div class="console-table-wrap">',
            '<div class="console-table-wrap console-table-wrap--scroll">',
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            print(f"  {name} scroll wrap")


def patch_site_map() -> None:
    path = T / "site_map.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '<h2 class="text-[11px] font-black text-slate-900 leading-none">Smart Panel</h2>',
        '<h2 class="text-sm font-semibold text-slate-900 leading-none">Smart panel</h2>',
    )
    text = text.replace("font-black", "font-semibold")
    text = text.replace("text-transform: uppercase;", "")
    path.write_text(text, encoding="utf-8")
    print("  site_map.html")


def patch_home() -> None:
    path = T / "home.html"
    text = path.read_text(encoding="utf-8")
    text2 = text.replace(
        '<p class="text-[10px] font-semibold tracking-[0.22em] text-emerald-600 dark:text-emerald-300">Online</p>',
        '<p class="console-stat-label text-emerald-600 dark:text-emerald-300">Online</p>',
    )
    if text2 != text:
        path.write_text(text2, encoding="utf-8")
        print("  home.html")


def patch_applicants_actions() -> None:
    path = T / "guarding/applicants.html"
    text = path.read_text(encoding="utf-8")
    old = """    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Applicants" page_subtitle="Recruitment pipeline" %}
        <button type="button" @click="createModal = true" class="btn-console shrink-0">New applicant</button>
    </div>"""
    new = """    <div class="console-page-toolbar">
        {% include "dashboard/partials/console/page_header.html" with page_title="Applicants" page_subtitle="Recruitment pipeline" %}
        <div class="console-page-actions">
            <button type="button" @click="createModal = true" class="btn-console">New applicant</button>
        </div>
    </div>"""
    if patch(path, old, new):
        print("  guarding_applicants.html actions")


def main() -> None:
    print("Phase 3 patches:")
    patch_site_console()
    patch_site_update()
    patch_onboard()
    patch_emergency_services()
    patch_guards()
    add_scroll_wraps()
    patch_site_map()
    patch_home()
    patch_applicants_actions()


if __name__ == "__main__":
    main()
