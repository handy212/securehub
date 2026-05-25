#!/usr/bin/env python3
"""Phase 6: re-port site_console.html to design-system shells."""
from __future__ import annotations

from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "backend/apps/dashboard/templates/dashboard/sites/console.html"

REPLACEMENTS = [
    (
        'class="bg-white rounded border border-slate-200 px-3 py-2 flex items-center gap-2.5 shadow-sm"',
        'class="console-table-card px-3 py-2 flex items-center gap-2.5"',
    ),
    (
        'class="bg-white rounded border border-slate-200 shadow-sm overflow-hidden flex flex-col"',
        'class="console-table-card overflow-hidden flex flex-col"',
    ),
    (
        'class="bg-white rounded border border-slate-200 shadow-sm overflow-hidden"',
        'class="console-table-card overflow-hidden"',
    ),
    (
        'class="bg-white rounded border border-slate-200 shadow-sm p-4 space-y-2"',
        'class="console-table-card p-4 space-y-2"',
    ),
    (
        'class="bg-white rounded-2xl border border-slate-100 shadow-sm px-4 py-3 space-y-2"',
        'class="console-table-card px-4 py-3 space-y-2"',
    ),
    (
        'class="bg-white rounded-2xl border border-slate-100 shadow-sm px-4 py-3 space-y-3"',
        'class="console-table-card px-4 py-3 space-y-3"',
    ),
    (
        'class="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"',
        'class="console-table-card overflow-hidden"',
    ),
    (
        'class="mb-4 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden"',
        'class="mb-4 console-table-card overflow-hidden"',
    ),
    (
        'class="absolute right-0 mt-2 w-52 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden"',
        'class="console-dropdown-menu absolute right-0 mt-2 w-52 z-50"',
    ),
    (
        'class="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-400 hover:text-slate-900 hover:border-slate-300 transition-all shadow-sm"',
        'class="btn-console-secondary !min-h-0 p-1.5 shadow-sm"',
    ),
    (
        'class="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-600 hover:bg-slate-50 transition-all flex items-center gap-1.5 shadow-sm"',
        'class="btn-console-secondary !min-h-0 py-1.5 text-[11px] flex items-center gap-1.5 shadow-sm"',
    ),
    (
        'class="text-[9px] font-bold text-slate-400"',
        'class="console-stat-label"',
    ),
    (
        'class="text-[9px] font-medium text-slate-400"',
        'class="console-meta"',
    ),
    (
        'class="text-[9px] text-slate-500"',
        'class="console-meta"',
    ),
    (
        'class="text-[9px] text-slate-400"',
        'class="console-meta"',
    ),
    (
        'class="text-[8px] font-bold text-slate-400"',
        'class="console-meta text-[10px]"',
    ),
    (
        'class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-[9px] font-bold text-amber-700"',
        'class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 console-meta text-amber-700"',
    ),
    (
        'class="text-[9px] font-bold ml-2 uppercase"',
        'class="console-meta ml-2 capitalize"',
    ),
    (
        'class="text-[9px] font-bold text-slate-400 uppercase tracking-tighter leading-none mt-0.5"',
        'class="console-meta leading-none mt-0.5 capitalize"',
    ),
    (
        'class="btn-premium w-full py-3 from-brand to-brand-700 text-white text-xs shadow-lg shadow-brand/20"',
        'class="btn-console w-full justify-center py-2.5"',
    ),
    (
        'class="btn-premium w-full py-3 from-emerald-500 to-emerald-700 text-white text-xs shadow-lg shadow-emerald-100"',
        'class="btn-console w-full justify-center py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white"',
    ),
    (
        'class="btn-premium w-full py-3 from-slate-700 to-slate-900 text-white text-xs shadow-lg shadow-slate-200"',
        'class="btn-console-secondary w-full justify-center py-2.5"',
    ),
    (
        'class="btn-premium w-full py-3 mt-4 from-slate-700 to-slate-900 text-white console-label shadow-lg shadow-slate-200"',
        'class="btn-console-secondary w-full justify-center py-2.5 mt-4"',
    ),
]


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    PATH.write_text(text, encoding="utf-8")
    print("  site_console.html phase 6 bulk replacements done")


if __name__ == "__main__":
    main()
