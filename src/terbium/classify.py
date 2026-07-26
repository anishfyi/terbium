"""Document classification from page-level signals.

Runs after adapter parse and before schema routing. Catalog/lookbook inputs keep
their existing behavior; other doc types route to transaction/resume/table lanes.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .layout import signals
from .layout.lines import cluster_lines
from .model.elements import Page

DOC_TYPES = (
    "catalog", "lookbook", "transaction", "resume", "table", "deck", "unknown",
)

# keyword buckets scored per page, summed for the document
_TRANSACTION_KW = re.compile(
    r"\b(invoice|receipt|bill to|ship to|total due|amount due|subtotal|"
    r"purchase order|po number|quote|tax id|vat|gst)\b",
    re.IGNORECASE,
)
_RESUME_KW = re.compile(
    r"\b(resume|curriculum vitae|experience|education|skills|certification|"
    r"employment|objective|references)\b",
    re.IGNORECASE,
)
_CATALOG_KW = re.compile(
    r"\b(catalogue|catalog|collection|sku|article|product|material|ingredients)\b",
    re.IGNORECASE,
)
_DECK_KW = re.compile(r"\b(slide|agenda|overview|presentation)\b", re.IGNORECASE)

_COLON_KV = re.compile(r"^[A-Za-z][A-Za-z0-9 /&().-]{0,40}:\s*\S", re.MULTILINE)


def _page_text(page: Page) -> str:
    return "\n".join(ln.text for ln in cluster_lines(page.words) if ln.text.strip())


def _image_density(page: Page) -> float:
    if not page.images or not page.width or not page.height:
        return 0.0
    area = page.width * page.height
    img_area = sum((im.width * im.height) for im in page.images)
    return min(1.0, img_area / max(area, 1.0) / 4.0)


def _photo_count(page: Page) -> int:
    return sum(1 for im in page.images if im.kind == "photo")


def _score_page(page: Page) -> Dict[str, float]:
    text = _page_text(page)
    low = text.lower()
    scores: Dict[str, float] = {t: 0.0 for t in DOC_TYPES}

    photos = _photo_count(page)
    img_den = _image_density(page)
    has_native = bool(page.native_tables)

    # transaction signals
    if _TRANSACTION_KW.search(text):
        scores["transaction"] += 2.0
    amounts = len(signals.find_amounts(text))
    dates = len(signals.find_dates(text))
    if amounts >= 2:
        scores["transaction"] += 1.0 + min(2.0, amounts * 0.3)
    if dates >= 1 and amounts >= 1:
        scores["transaction"] += 0.5
    if signals.find_invoice_numbers(text):
        scores["transaction"] += 1.0
    if _COLON_KV.findall(text):
        scores["transaction"] += 0.5

    # resume signals
    if _RESUME_KW.search(text):
        scores["resume"] += 2.0
    if signals.find_emails(text):
        scores["resume"] += 0.8
    if signals.find_phones(text):
        scores["resume"] += 0.5
    # section headers: bold or large font lines
    lines = cluster_lines(page.words)
    med = page.median_size or 12.0
    section_hits = sum(1 for ln in lines if ln.any_bold or ln.max_size >= med * 1.15)
    if section_hits >= 2 and _RESUME_KW.search(text):
        scores["resume"] += 1.0

    # catalog / lookbook
    if _CATALOG_KW.search(text):
        scores["catalog"] += 1.0
    if photos >= 3 and img_den > 0.05:
        scores["lookbook"] += 1.5
    elif photos >= 1:
        scores["lookbook"] += 0.8
        scores["catalog"] += 0.5
    if signals.find_skus(text):
        scores["catalog"] += 0.8

    # table / pricelist
    if has_native:
        scores["table"] += 2.0
    if amounts >= 3 and photos < 2:
        scores["table"] += 1.0

    # deck
    if page.source_kind == "pptx":
        scores["deck"] += 2.0
    if _DECK_KW.search(text) and photos <= 2:
        scores["deck"] += 0.5

    # unknown baseline
    if not text.strip() and photos:
        scores["unknown"] += 0.5

    return scores


def classify(pages: List[Page]) -> Tuple[str, Dict[str, float]]:
    """Return (doc_type, scores) from page-level signals."""
    if not pages:
        return "unknown", {t: 0.0 for t in DOC_TYPES}

    totals: Dict[str, float] = {t: 0.0 for t in DOC_TYPES}
    for p in pages:
        ps = _score_page(p)
        for k, v in ps.items():
            totals[k] += v

    # PPTX defaults to deck unless strong transaction/resume signals
    if pages[0].source_kind == "pptx" and totals["deck"] >= totals["transaction"]:
        if totals["transaction"] < totals["deck"] + 1:
            return "deck", totals

    best = max(totals, key=lambda k: totals[k])
    if totals[best] < 0.5:
        return "unknown", totals

    # catalog vs lookbook: lookbook wins when image-heavy and weak table signals
    if best in ("catalog", "lookbook"):
        if totals["lookbook"] > totals["catalog"] and totals["table"] < 2:
            return "lookbook", totals
        if totals["catalog"] >= totals["lookbook"]:
            return "catalog", totals
        return "lookbook", totals

    return best, totals


def schema_for_type(doc_type: str) -> str:
    """Map a classified doc type to the default schema name."""
    return {
        "catalog": "product",
        "lookbook": "product",
        "transaction": "transaction",
        "resume": "resume",
        "table": "product",
        "deck": "generic",
    }.get(doc_type, "generic")
