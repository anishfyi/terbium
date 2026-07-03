"""AI fill for the catalog table: read the product photo + page text, return the
name, SKU, and materials/ingredients the deterministic pass could not see.

This is the "works for anything" layer. Vendor catalogues bury materials in prose
("crafted from solid mango wood") and often show a code only in the artwork; a
vision model reading the image alongside the page text recovers both. It only
fills blanks, never overwrites a value the deterministic pass was sure of, and is
a no-op without a key.
"""
from __future__ import annotations

import json
import os
import re
from typing import List

from . import router
from .providers import vision_provider

SYSTEM = (
    "You extract one product's catalogue data. You are given a product photo and "
    "the text near it on the page. Return ONLY JSON: "
    '{"name": <string|null>, "sku": <string|null>, "materials": <string|null>}. '
    "materials is the product's materials or ingredients (read the image and the "
    "text, e.g. 'solid mango wood', '100% wool', 'aqua, glycerin'). Do NOT invent a "
    "SKU or a material that is not supported by the text or clearly visible."
)


def _extract_json(raw: str):
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def enrich_catalog(rows: List[dict], path: str, images_dir, ai) -> List[dict]:
    provider = vision_provider(ai)
    if provider is None:
        return rows
    tier = ai.force_tier or router.SONNET
    for row in rows:
        if row.get("sku") and row.get("materials") and row.get("name"):
            continue                       # deterministic pass already complete
        image = None
        if images_dir and row.get("image"):
            try:
                with open(os.path.join(images_dir, row["image"]), "rb") as fh:
                    image = fh.read()
            except OSError:
                image = None
        prompt = (
            f"Text near this product:\n{row.get('_context', '')[:1200]}\n\n"
            "Return the product's name, sku, and materials as JSON."
        )
        try:
            raw = provider.complete(prompt, SYSTEM, tier, image_png=image)
            data = _extract_json(raw)
        except Exception:
            data = None
        if data:
            for key in ("name", "sku", "materials"):
                if not row.get(key) and data.get(key):
                    row[key] = data[key]
    return rows
