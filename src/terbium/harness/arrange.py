"""The AI 'arrange' step: rebuild the tables the engine could not resolve.

Only hard tables reach here. Each is handed to the routed model with the page's
raw text lines and (for PDFs) a rendered image, and asked to return the clean
matrix as JSON. terbium then trusts the AI's structure for those tables and
marks the records' origin as 'ai'.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional

from ..model.elements import Page
from ..model.table import ExtractedTable
from ..layout.lines import cluster_lines
from . import router
from .ai import AI
from .providers import text_provider

SYSTEM = (
    "You are terbium's arrange step. You are given a raw, positionally-scrambled "
    "dump of one document page plus terbium's best-effort guess at a product "
    "table on it. Rebuild the table faithfully: identify the column headers "
    "(e.g. finishes/colours), the row headers (e.g. sizes/dimensions), and place "
    "every article number into its correct cell. Return ONLY JSON."
)

_JSON_SCHEMA_HINT = (
    '{"title": <string|null>, "col_headers": [<string>...], '
    '"rows": [{"row_header": <string>, "cells": [<string|null>...]}...], '
    '"attributes": {<key>: <string>}}'
)


def _page_text(pages: List[Page], index: int) -> str:
    for p in pages:
        if p.index == index:
            return "\n".join(ln.text for ln in cluster_lines(p.words) if ln.text)
    return ""


def _page(pages: List[Page], index: int) -> Optional[Page]:
    for p in pages:
        if p.index == index:
            return p
    return None


def _build_prompt(table: ExtractedTable, context: str) -> str:
    best = {
        "title": table.title,
        "col_headers": table.col_headers,
        "row_headers": table.row_headers,
        "cells": table.cells,
    }
    return (
        f"RAW PAGE TEXT (order is unreliable):\n{context}\n\n"
        f"TERBIUM BEST-EFFORT TABLE:\n{json.dumps(best, ensure_ascii=False)}\n\n"
        f"Return corrected JSON in exactly this shape:\n{_JSON_SCHEMA_HINT}"
    )


def _extract_json(raw: str) -> Optional[dict]:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def _apply(table: ExtractedTable, data: dict, tier: str) -> None:
    if data.get("title"):
        table.title = data["title"]
    table.col_headers = [str(h) for h in data.get("col_headers", table.col_headers)]
    rows = data.get("rows")
    if isinstance(rows, list) and rows:
        table.row_headers = [str(r.get("row_header", "")) for r in rows]
        table.cells = [[(c if c else None) for c in r.get("cells", [])] for r in rows]
    if isinstance(data.get("attributes"), dict):
        table.attributes.update({k: str(v) for k, v in data["attributes"].items()})
    table.confidence = 0.92
    table.origin = "ai"
    table.reasons = [f"arranged by AI ({tier})"]


def arrange_tables(path: str, pages: List[Page], hard_tables: List[ExtractedTable], ai: AI) -> int:
    """Rewrite hard tables in place using the AI lane. Returns how many succeeded."""
    provider = text_provider(ai)
    if provider is None:
        return 0
    fixed = 0
    for t in hard_tables:
        tier = router.pick_tier(t, ai.force_tier)
        context = _page_text(pages, t.source_page)
        image = None
        page = _page(pages, t.source_page)
        if ai.has_vision and page is not None and page.source_kind == "pdf":
            try:
                from ..documents.pdf import render_page_png

                image = render_page_png(path, t.source_page)
            except Exception:
                image = None
        try:
            raw = provider.complete(_build_prompt(t, context), SYSTEM, tier, image_png=image)
            data = _extract_json(raw)
            if data:
                _apply(t, data, tier)
                fixed += 1
        except Exception:
            continue
    return fixed
