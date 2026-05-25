#!/usr/bin/env python3
"""Phase 5: site console, broadcast, and remaining typography (safe replacements)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "backend/apps/dashboard/templates/dashboard"


def patch_site_console() -> None:
    path = T / "sites/console.html"
    text = path.read_text(encoding="utf-8")

    pairs = [
        ('<p class="text-[10px] font-black text-slate-900">Site Pending Activation</p>', '<p class="console-alert-title">Site pending activation</p>'),
        ('<p class="text-[10px] font-bold text-slate-600 mt-0.5">', '<p class="console-meta mt-0.5">'),
        ('<div class="text-xs font-black text-slate-900 dark:text-slate-100" x-text="siteStatus.armed"', '<div class="console-stat-value-xs" x-text="siteStatus.armed"'),
        ('<div class="text-xs font-black" :class="siteStatus.alarms > 0', '<div class="console-stat-value-xs" :class="siteStatus.alarms > 0'),
        ('<div class="text-xs font-black text-slate-900 dark:text-slate-100">{{ subscription.status }}</div>', '<div class="console-stat-value-xs">{{ subscription.status }}</div>'),
        ('<div class="text-xs font-black text-slate-400">No Plan</div>', '<div class="console-stat-value-xs text-slate-400">No plan</div>'),
        ('text-[10px] font-black text-slate-400', 'console-meta'),
        ('text-[10px] font-bold text-slate-400', 'console-meta'),
        ('text-[10px] font-bold text-slate-300', 'console-meta text-slate-300'),
        ('<h3 class="text-xs font-black text-slate-900 truncate leading-tight">', '<h3 class="console-panel-title truncate text-xs">'),
        ('<span class="text-[12px] font-black text-slate-900">', '<span class="console-stat-value text-xs">'),
        ('<span class="text-[11px] font-black ', '<span class="console-stat-value text-[11px] '),
        ('<p class="mt-1 text-sm font-black text-slate-900">', '<p class="mt-1 console-stat-value text-sm">'),
        ('<p class="mt-1 text-[11px] font-black text-slate-900">', '<p class="mt-1 console-stat-value text-[11px]">'),
        ('<div class="rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2">', '<div class="console-kpi-tile">'),
        ('<span class="text-[10px] font-bold text-slate-800" x-text="fault.label">', '<span class="console-label text-slate-800" x-text="fault.label">'),
        ('<span class="text-xs font-black text-slate-800" x-text="sub.name">', '<span class="console-row-title" x-text="sub.name">'),
        ('<span class="text-[10px] font-bold ml-2 uppercase"', '<span class="console-count-pill ml-2"'),
        ('class="text-[10px] font-black text-brand hover:underline">View Archives</a>', 'class="console-text-link">View archives</a>'),
        ('<div class="py-20 text-center text-[10px] text-slate-300 font-semibold tracking-widest">No Recent Logs</div>', '<div class="console-empty-state">No recent logs</div>'),
        ('<span class="text-[10px] font-black text-white/50 uppercase"', '<span class="console-meta text-white/50"'),
        ('<span class="font-bold text-slate-400 uppercase">Status</span>', '<span class="console-label text-slate-400">Status</span>'),
        ('<span class="font-bold text-slate-400 uppercase">Last Sync</span>', '<span class="console-label text-slate-400">Last sync</span>'),
        ('class="btn-console-secondary !min-h-0 py-1.5 text-[11px] font-bold normal-case tracking-normal', 'class="btn-console-secondary !min-h-0 py-1.5 text-[11px]'),
        ('class="w-full text-left px-3 py-2.5 text-[11px] font-bold text-red-500', 'class="w-full text-left px-3 py-2.5 text-[11px] font-semibold text-red-500'),
        ('leading-relaxed er">', 'leading-relaxed">'),
    ]
    for old, new in pairs:
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")
    print("  site_console.html")


def patch_broadcast() -> None:
    path = T / "broadcast.html"
    if not path.exists():
        return
    pairs = [
        ('<p class="text-[11px] font-black text-amber-800">FCM Core Unavailable</p>', '<p class="console-alert-title text-amber-800">FCM core unavailable</p>'),
        ('<p class="text-lg font-black text-slate-900 dark:text-slate-100 leading-none mt-1">', '<p class="console-stat-value leading-none mt-1">'),
        ('<span class="text-[10px] font-black"', '<span class="console-meta"'),
        ('<p class="text-[10px] font-black text-white truncate"', '<p class="console-meta text-white truncate"'),
        ('<p class="text-[11px] font-black text-slate-900 truncate">', '<p class="console-row-title truncate">'),
        ('<p class="text-[11px] font-black text-slate-900 dark:text-slate-100 mb-1"', '<p class="console-row-title mb-1"'),
    ]
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("  broadcast.html")


def patch_guarding_overview() -> None:
    path = T / "guarding/overview.html"
    pairs = [
        ('class="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-red-600 text-sm font-black tabular-nums text-white"', 'class="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-red-600 console-stat-value text-sm text-white"'),
        ('class="shrink-0 text-[10px] font-bold tabular-nums', 'class="console-time-meta'),
        ('class="mt-0.5 line-clamp-2 text-[10px] font-bold text-slate-500', 'class="console-meta mt-0.5 line-clamp-2'),
        ('class="mt-1 text-[10px] font-bold text-slate-500', 'class="console-meta mt-1'),
    ]
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("  guarding_overview.html")


def patch_guarding_backoffice() -> None:
    path = T / "guarding/backoffice.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace('class="font-black text-slate-900 dark:text-slate-100"', 'class="console-row-title"')
    text = text.replace("<b>", '<span class="font-semibold">').replace("</b>", "</span>")
    path.write_text(text, encoding="utf-8")
    print("  guarding_backoffice.html")


def patch_guarding_analytics() -> None:
    path = T / "guarding/analytics.html"
    text = path.read_text(encoding="utf-8")
    text2 = text.replace('class="mt-1 text-2xl font-black', 'class="mt-1 console-stat-value text-2xl')
    if text2 != text:
        path.write_text(text2, encoding="utf-8")
        print("  guarding_analytics.html")


def main() -> None:
    print("Phase 5 patches:")
    patch_site_console()
    patch_broadcast()
    patch_guarding_overview()
    patch_guarding_backoffice()
    patch_guarding_analytics()


if __name__ == "__main__":
    main()
