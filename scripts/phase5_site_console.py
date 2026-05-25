#!/usr/bin/env python3
"""Modernize site_console typography to design-system classes (safe regex)."""
from __future__ import annotations

import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "backend/apps/dashboard/templates/dashboard/sites/console.html"


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    # Micro labels (all sizes)
    text = re.sub(
        r"text-\[(?:8|9|10)px\] font-black uppercase tracking-widest",
        "console-label",
        text,
    )
    text = re.sub(
        r"text-\[10px\] font-black uppercase tracking-tighter",
        "console-label",
        text,
    )
    text = re.sub(
        r"text-\[11px\] font-black uppercase tracking-tight",
        "console-row-title",
        text,
    )
    text = re.sub(
        r"text-xs font-black uppercase tracking-tight",
        "console-row-title",
        text,
    )
    text = re.sub(
        r"text-xs font-black text-slate-800 uppercase tracking-tight",
        "console-row-title",
        text,
    )

    # Stat values
    text = text.replace(
        'class="text-xs font-black text-slate-900" x-text="siteStatus.armed"',
        'class="console-stat-value-xs" x-text="siteStatus.armed"',
    )
    text = text.replace(
        'class="text-xs font-black uppercase" :class="siteStatus.offline',
        'class="console-stat-value-xs" :class="siteStatus.offline',
    )
    text = text.replace(
        'class="text-xs font-black text-slate-900 uppercase tracking-tight"',
        'class="console-stat-value-xs"',
    )
    text = text.replace(
        'class="text-xs font-black text-slate-400 uppercase tracking-tight"',
        'class="console-stat-value-xs text-slate-400"',
    )
    text = text.replace(
        'class="text-[9px] font-black text-slate-900" x-text="event.occurredAtTime"',
        'class="console-time-meta text-slate-900" x-text="event.occurredAtTime"',
    )

    # Alerts / pending
    text = text.replace(
        '<p class="console-label text-slate-900 uppercase ">Site Pending Activation</p>',
        '<p class="console-alert-title">Site pending activation</p>',
    )
    text = text.replace(
        '<p class="text-[10px] font-black text-slate-900 uppercase tracking-widest">Site Pending Activation</p>',
        '<p class="console-alert-title">Site pending activation</p>',
    )

    # Inventory / KPI numbers
    text = re.sub(
        r'<p class="mt-1 text-sm font-black text-slate-900">',
        '<p class="mt-1 console-stat-value text-sm">',
        text,
    )
    text = re.sub(
        r'<p class="mt-1 text-\[11px\] font-black text-slate-900">',
        '<p class="mt-1 console-stat-value text-[11px]">',
        text,
    )
    text = re.sub(
        r'<div class="rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2">',
        '<div class="console-kpi-tile">',
        text,
    )

    # Links
    text = text.replace(
        'class="text-[9px] font-black text-brand uppercase tracking-widest hover:underline">View Archives</a>',
        'class="console-text-link">View archives</a>',
    )

    # Empty states
    text = text.replace(
        '<div class="py-20 text-center text-[10px] text-slate-300 font-black uppercase tracking-widest">No Recent Logs</div>',
        '<div class="console-empty-state">No recent logs</div>',
    )

    # Buttons: strip shouty caps from inline button classes (keep btn-* where present)
    text = re.sub(
        r" text-\[(?:8|9|10|11)px\] font-black uppercase tracking-widest",
        "",
        text,
    )
    text = re.sub(
        r" uppercase tracking-widest",
        "",
        text,
    )

    # Hardware modal labels
    text = re.sub(
        r'<label class="text-\[9px\] font-black text-slate-400 uppercase tracking-widest">',
        '<label class="console-label text-slate-400">',
        text,
    )

    # Subscription rate lines
    text = text.replace(
        '<span class="text-[12px] font-black text-slate-900">',
        '<span class="console-stat-value text-xs">',
    )
    text = text.replace(
        '<span class="text-[11px] font-black ',
        '<span class="console-stat-value text-[11px] ',
    )

    # Picture modal
    text = text.replace(
        '<span class="text-[10px] font-black text-white/50 uppercase"',
        '<span class="console-meta text-white/50"',
    )

    PATH.write_text(text, encoding="utf-8")
    remaining = len(re.findall(r"font-black", text))
    print(f"site_console.html updated ({remaining} font-black left)")


if __name__ == "__main__":
    main()
