"""AI product enrichment: the layer that makes terbium work for anything.

Given a product's deterministically-extracted fields, and optionally its photo,
a routed model returns one normalized product record: it infers the category and
its category-appropriate attributes, both explicit (in the text) and implicit
(read from the image, e.g. pattern, weave, style), and normalizes price and
dimensions. It is opt-in, confidence-gated, and never invents facts.

This is the technique now shipped by Shopify, Amazon, and PIM vendors, brought
inside terbium's deterministic-first pipeline so a model is only called on the
products that actually need it.
"""
from __future__ import annotations

import json
import re
from typing import Callable, List, Optional

from ..model.record import Record
from . import router
from .ai import AI
from .providers import text_provider, vision_provider

SYSTEM = (
    "You are terbium's product enrichment step. You are given one vendor product's "
    "raw extracted fields, and sometimes its photo. Return ONE normalized product "
    "record as JSON. Infer the product category and its category-appropriate "
    "attributes, both explicit (present in the text) and implicit (clearly visible "
    "in the image, such as colour, pattern, material, shape, or style). Normalize "
    "price to {amount, currency} and dimensions to a clean string. Do NOT invent "
    "facts that are not supported by the text or the image. Return ONLY JSON."
)

_SCHEMA_HINT = (
    '{"name": <string>, "sku": <string|null>, "category": <string>, '
    '"price": {"amount": <number|null>, "currency": <string|null>}, '
    '"dimensions": <string|null>, "color": <string|null>, "material": <string|null>, '
    '"attributes": {<key>: <value>}, "confidence": <0..1>}'
)


def _build_prompt(fields: dict, has_image: bool) -> str:
    img_line = "A photo of the product is attached; read implicit attributes from it.\n" if has_image else ""
    return (
        f"{img_line}RAW FIELDS:\n{json.dumps(fields, ensure_ascii=False)}\n\n"
        f"Return corrected, enriched JSON in exactly this shape:\n{_SCHEMA_HINT}"
    )


def _extract_json(raw: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _apply(record: Record, data: dict) -> Record:
    fields = dict(record.fields)
    for key in ("name", "category", "dimensions", "color", "material"):
        if data.get(key):
            fields[key] = data[key]
    price = data.get("price")
    if isinstance(price, dict):
        if price.get("amount") is not None:
            fields["price_amount"] = price["amount"]
        if price.get("currency"):
            fields["currency"] = price["currency"]
    if isinstance(data.get("attributes"), dict):
        for k, v in data["attributes"].items():
            fields.setdefault(k, v)
    sku = data.get("sku") or record.sku
    conf = data.get("confidence")
    return Record(
        sku=sku,
        fields=fields,
        source_page=record.source_page,
        confidence=float(conf) if isinstance(conf, (int, float)) else max(record.confidence, 0.9),
        reasons=["enriched by AI"],
        origin="ai",
    )


def enrich_records(
    records: List[Record],
    ai: AI,
    image_for: Optional[Callable[[Record], Optional[bytes]]] = None,
    only_below: float = 1.01,
    tier: str = router.SONNET,
) -> List[Record]:
    """Enrich product records with a routed model. Returns a new list.

    ``image_for(record) -> png bytes | None`` supplies a product photo for implicit
    attribute reads. ``only_below`` enriches just records under that confidence
    (default: all). Records are left untouched if the AI lane is unavailable.
    """
    if not ai or not ai.available:
        return records
    provider = vision_provider(ai) if image_for else text_provider(ai)
    if provider is None:
        return records
    pick_tier = ai.force_tier or tier
    out: List[Record] = []
    for r in records:
        if r.confidence >= only_below:
            out.append(r)
            continue
        image = image_for(r) if image_for else None
        try:
            raw = provider.complete(_build_prompt(r.fields, image is not None), SYSTEM, pick_tier, image_png=image)
            data = _extract_json(raw)
            out.append(_apply(r, data) if data else r)
        except Exception:
            out.append(r)
    return out
