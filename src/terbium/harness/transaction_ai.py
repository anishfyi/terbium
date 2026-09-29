"""AI fill for transaction documents, modeled on catalog_ai.enrich_catalog."""
from __future__ import annotations

import json
import re
from typing import List, Tuple

from . import router
from .providers import text_provider
from ..model.record import Record

SYSTEM = (
    "You extract structured data from an invoice, bill, receipt, purchase order, "
    "or quote. Return ONLY JSON: "
    '{"number": <string|null>, "date": <string|null>, "vendor": <string|null>, '
    '"customer": <string|null>, "line_items": [{"description": <string>, '
    '"quantity": <string|null>, "unit_price": <string|null>, "amount": <string>}], '
    '"subtotal": <string|null>, "tax": <string|null>, "total": <string|null>}. '
    "Do NOT invent values not supported by the text."
)


def _extract_json(raw: str):
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def enrich_transactions(records: List[Record], page_text: str, ai) -> Tuple[List[Record], bool]:
    """Fill missing transaction fields via AI. Anthropic remains first-checked.

    Returns ``(records, called)``. ``called`` is True only when a model call
    returned a response, so callers can report AI use honestly.
    """
    provider = text_provider(ai)
    if provider is None:
        return records, False
    tier = ai.force_tier or router.SONNET
    summaries = [r for r in records if r.fields.get("record_type") == "summary"]
    if summaries and all(r.fields.get("total") for r in summaries):
        return records, False
    prompt = f"Document text:\n{page_text[:4000]}\n\nExtract transaction fields as JSON."
    try:
        raw = provider.complete(prompt, SYSTEM, tier)
    except Exception:
        return records, False
    data = _extract_json(raw)
    if not data:
        return records, True
    out: List[Record] = list(records)
    header_fields = {k: data[k] for k in ("number", "date", "vendor", "customer",
                                           "subtotal", "tax", "total") if data.get(k)}
    if header_fields:
        if summaries:
            for r in summaries:
                for k, v in header_fields.items():
                    if not r.fields.get(k):
                        r.fields[k] = v
        else:
            h = dict(header_fields)
            h["record_type"] = "summary"
            out.insert(0, Record(sku=h.get("number"), fields=h, source_page=0,
                                 confidence=0.85, origin="ai",
                                 reasons=["AI transaction summary"]))
    # Only add AI line items when the parser found none, so rows are not doubled.
    has_items = any(r.fields.get("record_type") == "line_item" for r in records)
    for item in ([] if has_items else data.get("line_items") or []):
        if not item.get("description"):
            continue
        fields = dict(header_fields)
        fields["record_type"] = "line_item"
        fields.update({k: v for k, v in item.items() if v})
        out.append(
            Record(sku=header_fields.get("number"), fields=fields, source_page=0,
                   confidence=0.8, origin="ai", reasons=["AI line item"])
        )
    return out, True
