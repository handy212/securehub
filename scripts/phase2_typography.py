#!/usr/bin/env python3
"""Phase 2: soften ALL-CAPS utility classes across dashboard templates."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "backend/apps/dashboard/templates/dashboard"

SKIP_FILES = frozenset(
    {
        "base.html",
        "guarding/_nav.html",
    }
)

REPLACEMENTS: list[tuple[str, str]] = [
    (
        "text-lg font-black text-slate-900 tracking-tight leading-none",
        "console-page-title leading-none",
    ),
    (
        "text-xl font-black text-slate-900 tracking-tight leading-none",
        "console-page-title leading-none",
    ),
    (
        "text-lg font-black text-slate-900 dark:text-slate-100 tracking-tight leading-none",
        "console-page-title leading-none",
    ),
    (
        "px-2 py-0.5 rounded bg-slate-100 text-slate-400 text-[10px] font-black uppercase tracking-wider",
        "console-count-chip",
    ),
    (
        "px-2 py-0.5 rounded-md bg-slate-100 text-slate-400 text-[10px] font-black uppercase tracking-wider",
        "console-count-chip",
    ),
    (
        "text-[10px] font-black text-slate-400 uppercase tracking-widest",
        "console-meta",
    ),
    (
        "text-[10px] font-bold text-slate-400 uppercase tracking-widest",
        "console-meta",
    ),
    (
        "text-[10px] font-black text-slate-500 uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[10px] font-bold text-slate-500 uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[11px] font-black text-slate-400 uppercase tracking-widest",
        "console-meta",
    ),
    (
        "text-[11px] font-bold text-slate-400 uppercase tracking-widest",
        "console-meta",
    ),
    (
        "text-[10px] font-black text-slate-600 uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[10px] font-bold text-slate-600 uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[10px] font-black text-slate-700 uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[10px] font-black text-slate-300 uppercase tracking-widest",
        "console-meta",
    ),
    (
        "text-[10px] font-black text-slate-400 uppercase tracking-wider",
        "console-meta",
    ),
    (
        "text-[10px] font-bold text-slate-400 uppercase tracking-wider",
        "console-meta",
    ),
    (
        "text-[10px] font-black uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[10px] font-bold uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[11px] font-black uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-[11px] font-bold uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-xs font-black uppercase tracking-widest",
        "console-label",
    ),
    (
        "text-xs font-bold uppercase tracking-widest",
        "console-label",
    ),
    (
        "px-4 py-2.5 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2",
        "console-search-bar",
    ),
    (
        "flex-1 bg-transparent text-[11px] font-bold text-slate-700 placeholder:text-slate-300 outline-none border-none shadow-none ring-0 h-auto py-0",
        "console-search-input",
    ),
    (
        "py-12 text-center text-[10px] font-black uppercase tracking-widest text-slate-400",
        "console-empty-state",
    ),
    (
        "py-8 text-center text-[10px] font-black uppercase tracking-widest text-slate-400",
        "console-empty-state",
    ),
]

# Segment / filter pill: keep structure, soften typography
SEGMENT_RE = re.compile(
    r"(\b(?:px-\d+|py-\d+)[^\"]*?)"
    r"text-\[10px\] font-black uppercase tracking-widest"
    r"([^\"]*?\brounded\b[^\"]*)",
)


def soften_segments(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        prefix, suffix = m.group(1), m.group(2)
        return f"{prefix}console-segment-link{suffix}"

    return SEGMENT_RE.sub(repl, text)


CLASS_ATTR_RE = re.compile(r'class="([^"]*)"')

TYPOGRAPHY_REMOVALS = [
    ("font-black uppercase", "font-semibold"),
    ("font-bold uppercase", "font-semibold"),
    ("uppercase tracking-widest", ""),
    ("uppercase tracking-wider", ""),
    ("uppercase tracking-tight", ""),
    ("uppercase tracking-tighter", ""),
]

BREADCRUMB_NAV_RE = re.compile(
    r'<nav class="flex items-center gap-2 (?:text-\[10px\] font-bold text-slate-400 uppercase tracking-widest|console-meta) mb-3">\s*'
    r'<a href="\{% url \'dashboard:home\' %\}" class="hover:text-brand transition-colors">Dashboard</a>\s*'
    r'<svg[^>]+></svg>\s*'
    r'(?:<a href="([^"]+)" class="hover:text-brand transition-colors">([^<]+)</a>\s*'
    r'<svg[^>]+></svg>\s*)?'
    r'<span class="text-slate-900">([^<]+)</span>\s*'
    r"</nav>",
    re.DOTALL,
)


def normalize_class_list(classes: str) -> str:
    for old, new in TYPOGRAPHY_REMOVALS:
        classes = classes.replace(old, new)
    parts = [p for p in classes.split() if p]
    return " ".join(parts)


def normalize_class_attrs(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'class="{normalize_class_list(m.group(1))}"'

    return CLASS_ATTR_RE.sub(repl, text)


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = soften_segments(text)
    text = normalize_class_attrs(text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed: list[str] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        if path.name in SKIP_FILES:
            continue
        if process_file(path):
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files:")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
