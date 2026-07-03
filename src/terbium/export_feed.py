"""Feed exporters: turn product records into commerce-ready files.

This is the payoff of the whole pipeline and the moat versus markdown parsers:
catalogue in, a Shopify product CSV or a clean PIM JSON out, ready to import.
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import List, Optional

from .model.record import Record

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(record: Record) -> str:
    base = record.fields.get("name") or record.sku or "product"
    return _SLUG_RE.sub("-", base.lower()).strip("-") or "product"


def _body(fields: dict) -> str:
    bits = []
    for key in ("material", "dimensions", "color"):
        if fields.get(key):
            bits.append(f"{key.title()}: {fields[key]}")
    return " | ".join(bits)


SHOPIFY_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published",
    "Option1 Name", "Option1 Value", "Variant SKU", "Variant Price",
    "Variant Inventory Qty", "Image Src",
]


def to_shopify_csv(records: List[Record], path: Optional[str] = None) -> str:
    """Render records as a Shopify product-import CSV. Writes to ``path`` if given."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SHOPIFY_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        f = r.fields
        color = f.get("color")
        tags = [t for t in (f.get("color_family"), f.get("material_family"), f.get("category")) if t]
        writer.writerow({
            "Handle": _slug(r),
            "Title": f.get("name") or (r.sku or ""),
            "Body (HTML)": _body(f),
            "Vendor": f.get("brand") or "",
            "Type": f.get("category") or "",
            "Tags": ", ".join(tags),
            "Published": "TRUE",
            "Option1 Name": "Color" if color else "Title",
            "Option1 Value": color or "Default Title",
            "Variant SKU": r.sku or "",
            "Variant Price": f.get("price_amount") if f.get("price_amount") is not None else "",
            "Variant Inventory Qty": f.get("quantity") or "",
            "Image Src": f.get("image") or f.get("image_file") or "",
        })
    out = buf.getvalue()
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
    return out


def to_pim_json(records: List[Record], path: Optional[str] = None) -> str:
    """Render records as a clean PIM/JSON feed (one object per product)."""
    items = []
    for r in records:
        item = {"sku": r.sku, "confidence": round(r.confidence, 3)}
        item.update(r.fields)
        items.append(item)
    out = json.dumps(items, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
    return out
