#!/usr/bin/env python3
"""Phase 7: finish typography migration — stats, shell chrome, auth, remaining list pages."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "backend/apps/dashboard/templates/dashboard"

REPLACEMENTS: list[tuple[str, str]] = [
    # ── Stat KPI values ──
    (
        'class="text-lg font-black text-slate-900 dark:text-slate-100"',
        'class="console-stat-value dark:text-slate-100"',
    ),
    (
        'class="text-lg font-black text-slate-900"',
        'class="console-stat-value"',
    ),
    (
        'class="text-lg font-black text-red-600 tabular-nums leading-none"',
        'class="console-stat-value text-red-600 tabular-nums leading-none"',
    ),
    (
        'class="text-lg font-black text-amber-600 tabular-nums leading-none"',
        'class="console-stat-value text-amber-600 tabular-nums leading-none"',
    ),
    (
        'class="text-lg font-black text-slate-900 tabular-nums leading-none"',
        'class="console-stat-value tabular-nums leading-none"',
    ),
    (
        'class="text-xl font-black text-emerald-700 dark:text-emerald-100 tabular-nums"',
        'class="console-stat-value text-emerald-700 dark:text-emerald-100 tabular-nums"',
    ),
    (
        'class="text-xl font-black text-red-600 dark:text-red-400 tabular-nums"',
        'class="console-stat-value text-red-600 dark:text-red-400 tabular-nums"',
    ),
    (
        'class="text-sm font-black text-slate-900 tabular-nums"',
        'class="console-stat-value-xs tabular-nums"',
    ),
    (
        'class="text-[10px] font-black text-slate-900 tabular-nums"',
        'class="console-stat-value-xs tabular-nums"',
    ),
    (
        'class="text-[10px] font-black text-emerald-600"',
        'class="console-stat-value-xs text-emerald-600"',
    ),
    (
        'class="text-xs font-black text-slate-900 dark:text-slate-100"',
        'class="console-stat-value-xs dark:text-slate-100"',
    ),
  (
        'class="text-[10px] font-black text-slate-700 leading-none"',
        'class="console-stat-value-xs leading-none"',
    ),
    # ── Row / cell titles ──
    (
        'class="text-[11px] font-black text-slate-800 hover:text-brand transition-colors leading-none"',
        'class="console-row-title leading-none hover:text-brand transition-colors"',
    ),
    (
        'class="text-[11px] font-black text-slate-800 truncate group-hover:text-brand transition-colors"',
        'class="console-row-title truncate group-hover:text-brand transition-colors"',
    ),
    (
        'class="text-[11px] font-black text-slate-900"',
        'class="console-row-title"',
    ),
    (
        'class="text-[11px] font-black text-slate-900 dark:text-slate-100"',
        'class="console-row-title"',
    ),
    (
        'class="text-[11px] font-black text-slate-300 tabular-nums w-5 text-center flex-shrink-0"',
        'class="console-meta tabular-nums w-5 text-center flex-shrink-0"',
    ),
    (
        'class="text-[11px] font-black text-slate-300 italic"',
        'class="console-empty-state italic"',
    ),
    (
        'class="text-xs font-black text-slate-800 dark:text-slate-100"',
        'class="console-row-title"',
    ),
    (
        'class="text-[10px] font-black text-slate-900"',
        'class="console-stat-value-xs"',
    ),
    (
        'class="text-[12px] font-black text-slate-900 leading-none"',
        'class="console-stat-value-xs leading-none"',
    ),
    # ── Onboard / alerts ──
    (
        'class="text-[10px] font-black text-slate-900"',
        'class="console-alert-title text-[10px]"',
    ),
    (
        'class="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[13px] font-black text-white"',
        'class="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[13px] font-semibold text-white"',
    ),
    (
        'class="min-w-0 flex-1 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[13px] font-mono font-black tracking-widest text-white outline-none"',
        'class="min-w-0 flex-1 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[13px] font-mono font-semibold tracking-wide text-white outline-none"',
    ),
    (
        'class="mt-0.5 font-black text-slate-900"',
        'class="mt-0.5 console-row-title"',
    ),
    (
        'class="mt-0.5 text-[10px] font-black text-slate-800"',
        'class="mt-0.5 console-stat-value-xs"',
    ),
    # ── Settings info cards ──
    (
        'class="text-xs font-black text-slate-900 dark:text-slate-100 mb-4"',
        'class="console-panel-title mb-4"',
    ),
    (
        'class="font-black text-slate-900 text-[10px] mb-1"',
        'class="console-label mb-1"',
    ),
    # ── Sites dropdown ──
    (
        'class="block px-3 py-2.5 text-[10px] font-black text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"',
        'class="console-dropdown-item"',
    ),
    (
        'class="w-full text-left px-3 py-2.5 text-[10px] font-black text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40"',
        'class="console-dropdown-item-danger"',
    ),
    # ── Shell chrome (base.html) ──
    (
        'class="font-black text-xs tracking-widest text-white uppercase whitespace-nowrap overflow-hidden"',
        'class="console-shell-brand whitespace-nowrap overflow-hidden"',
    ),
    (
        'class="truncate text-[10px] sm:text-xs font-black tracking-widest text-slate-400 uppercase"',
        'class="console-header-context"',
    ),
    (
        'class="hidden sm:inline text-[10px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-tight"',
        'class="hidden sm:inline console-label text-slate-700 dark:text-slate-300"',
    ),
    (
        'class="text-[11px] font-bold uppercase tracking-widest opacity-50"',
        'class="console-label capitalize opacity-50"',
    ),
    (
        'class="absolute right-4 top-4 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest"',
        'class="absolute right-4 top-4 console-palette-hint rounded border border-slate-200 px-1.5 py-0.5 dark:border-slate-700"',
    ),
    (
        'class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest"',
        'class="console-label"',
    ),
    (
        'class="text-[11px] font-black text-slate-900 dark:text-slate-100 uppercase tracking-tight"',
        'class="console-row-title"',
    ),
    (
        'class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest"',
        'class="console-meta"',
    ),
    (
        'class="text-[10px] font-black text-slate-800 dark:text-slate-200 uppercase tracking-widest"',
        'class="console-label"',
    ),
    (
        'class="p-12 text-center text-slate-300 dark:text-slate-600 uppercase tracking-widest font-black text-[10px]"',
        'class="console-empty-state p-12 text-center text-slate-300 dark:text-slate-600"',
    ),
    (
        'class="text-[10px] font-black text-slate-400 dark:text-slate-500"',
        'class="console-palette-hint"',
    ),
    (
        'class="text-[10px] font-black text-slate-300 dark:text-slate-600 uppercase italic hidden sm:inline"',
        'class="console-palette-hint hidden sm:inline italic"',
    ),
    # ── Auth pages ──
    (
        'class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]"',
        'class="console-meta"',
    ),
    (
        'class="text-sm font-black text-slate-900 dark:text-slate-100"',
        'class="console-panel-title"',
    ),
    # ── Guarding nav ──
    (
        'class="truncate text-[10px] font-black uppercase tracking-widest text-white"',
        'class="console-shell-brand truncate"',
    ),
    (
        'class="truncate text-[10px] font-bold uppercase tracking-widest text-slate-500"',
        'class="console-meta truncate"',
    ),
]

CLASS_ATTR_RE = re.compile(r'class="([^"]*)"')

TYPOGRAPHY_REMOVALS = [
    ("font-black uppercase", "font-semibold"),
    ("font-bold uppercase", "font-semibold"),
    ("uppercase tracking-widest", ""),
    ("uppercase tracking-wider", ""),
    ("uppercase tracking-tight", ""),
    ("uppercase tracking-tighter", ""),
    ("uppercase tracking-[0.2em]", ""),
    (" font-black", " font-semibold"),
]


def normalize_class_list(classes: str) -> str:
    for old, new in TYPOGRAPHY_REMOVALS:
        classes = classes.replace(old, new)
    parts = [p for p in classes.split() if p]
    return " ".join(parts)


def normalize_class_attrs(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'class="{normalize_class_list(m.group(1))}"'

    return CLASS_ATTR_RE.sub(repl, text)


def patch_sites_typo(text: str) -> str:
    return text.replace('class="console-meta mt-0.5 er"', 'class="console-meta mt-0.5"')


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = normalize_class_attrs(text)
    text = patch_sites_typo(text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed: list[str] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        if process_file(path):
            changed.append(str(path.relative_to(ROOT)))
    print(f"Phase 7 updated {len(changed)} files:")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
