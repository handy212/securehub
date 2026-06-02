"""Load and render SecureHub markdown documentation for the console help section."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.utils.safestring import mark_safe

DOCS_ROOT = Path(settings.BASE_DIR).parent / "docs"

HELP_SECTIONS: list[dict] = [
    {
        "title": "Start here",
        "pages": [
            {"slug": "index", "title": "Documentation hub", "file": "README.md"},
            {"slug": "system-overview", "title": "System overview", "file": "system-overview.md"},
            {"slug": "feature-guide", "title": "Feature guide", "file": "feature-guide.md"},
        ],
    },
    {
        "title": "User guides",
        "pages": [
            {"slug": "user-guide-staff-console", "title": "Staff console", "file": "user-guide-staff-console.md"},
            {"slug": "user-guide-guarding-ops", "title": "Guarding operations", "file": "user-guide-guarding-ops.md"},
            {"slug": "user-guide-guard-mobile", "title": "Field guard (mobile)", "file": "user-guide-guard-mobile.md"},
            {"slug": "user-guide-alarm-customer", "title": "Alarm customer", "file": "user-guide-alarm-customer.md"},
            {"slug": "user-guide-guarding-client", "title": "Guarding client portal", "file": "user-guide-guarding-client.md"},
        ],
    },
    {
        "title": "Technical reference",
        "pages": [
            {"slug": "access-control-matrix", "title": "Access control matrix", "file": "access-control-matrix.md"},
            {"slug": "operator-rbac", "title": "Operator RBAC", "file": "operator-rbac.md"},
            {"slug": "guard-mobile-api", "title": "Guard mobile API", "file": "guard-mobile-api.md"},
            {"slug": "emergency-addon-runbook", "title": "Emergency add-on runbook", "file": "emergency-addon-runbook.md"},
            {"slug": "guard-monitoring-system-roadmap", "title": "Guard monitoring roadmap", "file": "guard-monitoring-system-roadmap.md"},
            {"slug": "guard-monitoring-delivery-checklist", "title": "Delivery checklist", "file": "guard-monitoring-delivery-checklist.md"},
        ],
    },
]

_SLUG_INDEX: dict[str, dict] = {}
for section in HELP_SECTIONS:
    for page in section["pages"]:
        _SLUG_INDEX[page["slug"]] = {**page, "section": section["title"]}


def get_help_page(slug: str) -> dict | None:
    return _SLUG_INDEX.get(slug)


def help_nav_context(current_slug: str) -> dict:
    sections = []
    for section in HELP_SECTIONS:
        pages = []
        for page in section["pages"]:
            pages.append(
                {
                    **page,
                    "url": reverse("dashboard:help-page", kwargs={"slug": page["slug"]})
                    if page["slug"] != "index"
                    else reverse("dashboard:help-index"),
                    "is_active": page["slug"] == current_slug,
                }
            )
        sections.append({"title": section["title"], "pages": pages})
    return {"help_sections": sections, "help_current_slug": current_slug}


def _safe_doc_path(filename: str) -> Path:
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise Http404("Invalid document path.")
    path = (DOCS_ROOT / filename).resolve()
    try:
        if not path.is_relative_to(DOCS_ROOT.resolve()):
            raise Http404("Invalid document path.")
    except AttributeError:
        if DOCS_ROOT.resolve() not in path.parents and path != DOCS_ROOT.resolve():
            raise Http404("Invalid document path.")
    if not path.is_file():
        raise Http404("Document not found.")
    return path


def _rewrite_internal_links(html: str) -> str:
    def repl(match: re.Match) -> str:
        href = match.group(1)
        if ".." in href or "/" in href:
            return match.group(0)
        if href.startswith(("http://", "https://", "mailto:", "#", "/")):
            return match.group(0)
        base = Path(href).name
        if base.endswith(".md"):
            base = base[:-3]
        if base.upper() == "README":
            slug = "index"
        elif base in _SLUG_INDEX:
            slug = base
        else:
            return match.group(0)
        url = reverse("dashboard:help-index") if slug == "index" else reverse("dashboard:help-page", kwargs={"slug": slug})
        return f'href="{url}"'

    return re.sub(r'href="([^"]+)"', repl, html)


def _strip_leading_h1(html: str) -> str:
    """Page template already shows the title; drop duplicate markdown h1."""
    return re.sub(r"<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)


@lru_cache(maxsize=32)
def render_help_markdown(filename: str) -> str:
    import markdown as markdown_lib

    path = _safe_doc_path(filename)
    text = path.read_text(encoding="utf-8")
    html = markdown_lib.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        extension_configs={"fenced_code": {"lang_prefix": "language-"}},
    )
    html = _strip_leading_h1(_rewrite_internal_links(html))
    return mark_safe(html)  # noqa: S308 — trusted repo docs, staff-only
