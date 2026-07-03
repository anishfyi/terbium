"""Build the plain-language "bring an AI key" message.

This is terbium's signature behaviour: when the algorithmic engine cannot be
sure and no key is set, it says so, names the pages, gives the reasons, and
recommends a model tier. It never fails silently.
"""
from __future__ import annotations

from typing import List

from ..model.record import Record
from ..model.table import ExtractedTable
from . import router


def build_message(records: List[Record], hard_tables: List[ExtractedTable], threshold: float) -> str:
    total = len(records)
    confident = sum(1 for r in records if r.confidence >= threshold)
    pages = sorted({t.source_page + 1 for t in hard_tables})
    tier = router.recommend_tier(hard_tables)

    reasons: List[str] = []
    for t in hard_tables:
        for r in t.reasons:
            if r not in reasons:
                reasons.append(r)
    reason_str = "; ".join(reasons[:3]) if reasons else "uncertain structure"

    page_str = ", ".join(str(p) for p in pages[:8])
    if len(pages) > 8:
        page_str += ", ..."

    return (
        f"terbium: {confident}/{total} records parsed confidently.\n"
        f"{len(hard_tables)} table(s) on page(s) {page_str} are ambiguous "
        f"({reason_str}).\n"
        f"-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   "
        f"recommended tier: {tier.capitalize()}"
    )
