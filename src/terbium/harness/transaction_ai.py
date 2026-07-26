"""AI fill for transaction documents, modeled on catalog_ai.enrich_catalog."""
from __future__ import annotations

import json
import re
from typing import List

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


def enrich_transactions(records: List[Record], page_text: str, ai) -> List[Record]:
    """Fill missing transaction fields via AI. Anthropic remains first-checked."""
    provider = text_provider(ai)
    if provider is None:
        return records
    tier = ai.force_tier or router.SONNET
    if all(r.fields.get("total") for r in records if r.fields.get("record_type") == "header"):
        return records
    prompt = f"Document text:\n{page_text[:4000]}\n\nExtract transaction fields as JSON."
    try:
        raw = provider.complete(prompt, SYSTEM, tier)
        data = _extract_json(raw)
    except Exception:
        return records
    if not data:
        return records
    out: List[Record] = list(records)
    header_fields = {k: data[k] for k in ("number", "date", "vendor", "customer",
                                           "subtotal", "tax", "total") if data.get(k)}
    if header_fields:
        found_header = False
        for r in out:
            if r.fields.get("record_type") == "header":
                for k, v in header_fields.items():
                    r.fields.setdefault(k, v)
                found_header = True
        if not found_header:
            h = dict(header_fields)
            h["record_type"] = "header"
            out.insert(0, Record(sku=h.get("number"), fields=h, source_page=0,
                                 confidence=0.85, origin="ai",
                                 reasons=["AI transaction header"]))
    for item in data.get("line_items") or []:
        if not item.get("description"):
            continue
        fields = dict(header_fields)
        fields["record_type"] = "line_item"
        fields.update({k: v for k, v in item.items() if v})
        out.append(
            Record(sku=header_fields.get("number"), fields=fields, source_page=0,
                   confidence=0.8, origin="ai", reasons=["AI line item"])
        )
    return out
