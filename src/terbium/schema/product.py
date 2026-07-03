"""Universal product schema: category-agnostic column mapping.

Rugs, lamps, bags, cushions, handwash, whatever, a row-per-product catalogue is
the same shape: a header names each column, and terbium maps those headers to a
common product record by meaning. A bag's "capacity" and a lamp's "wattage" that
have no canonical slot are preserved as attributes, so nothing is lost and no
per-category schema has to be written.
"""
from __future__ import annotations

import re
from typing import List, Optional

from ..model.record import Record
from ..model.table import ExtractedTable
from .base import Schema, register_schema

# canonical field -> header substrings that map to it (checked most-specific first)
FIELD_SYNONYMS = [
    ("sku", ["article number", "article no", "item code", "product code", "style no",
             "style code", "model no", "part no", "barcode", "sku", "article", "ean",
             "upc", "ref", "reference", "code"]),
    ("name", ["product name", "item name", "style name", "model name", "description",
              "name", "product", "title", "item", "style"]),
    ("price", ["unit price", "wholesale", "retail price", "selling price", "price",
               "mrp", "srp", "msrp", "cost", "rate", "amount"]),
    ("dimensions", ["dimensions", "dimension", "measurements", "measurement", "size",
                    "dims", "l x w", "w x d"]),
    ("color", ["colour", "color", "shade", "tone", "finish"]),
    ("material", ["material", "fabric", "composition", "upholstery", "filling",
                  "fill", "fibre", "fiber", "made of"]),
    ("category", ["category", "collection", "range", "department", "type", "group"]),
    ("quantity", ["pack size", "moq", "quantity", "qty", "stock", "units", "carton"]),
    ("weight", ["gross weight", "net weight", "weight", "wt"]),
    ("brand", ["brand", "vendor", "supplier", "manufacturer", "make"]),
]

_CURRENCY = {"$": "USD", "£": "GBP", "€": "EUR", "₹": "INR", "rs": "INR", "rs.": "INR"}
_PRICE_RE = re.compile(r"([$£€₹]|rs\.?|inr|usd|gbp|eur)?\s*([\d][\d,]*\.?\d*)", re.IGNORECASE)
_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/\-]{2,15}$")


def _map_header(header: str) -> Optional[str]:
    """Map a column header to a canonical field by the longest matching synonym,
    so 'pack size' -> quantity beats 'size' -> dimensions."""
    h = (header or "").strip().lower()
    if not h:
        return None
    best, best_len = None, 0
    for canonical, subs in FIELD_SYNONYMS:
        for s in subs:
            if s in h and len(s) > best_len:
                best, best_len = canonical, len(s)
    return best


def _price(value: str):
    m = _PRICE_RE.search(value or "")
    if not m:
        return None, None
    sym = (m.group(1) or "").lower()
    currency = _CURRENCY.get(sym) or (sym.upper() if sym else None)
    amount = m.group(2).replace(",", "")
    try:
        return float(amount), currency
    except ValueError:
        return None, currency


def _looks_like_sku(value: str) -> bool:
    v = (value or "").strip()
    return bool(_CODE_RE.match(v)) and any(c.isdigit() for c in v)


@register_schema
class ProductSchema(Schema):
    name = "product"

    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        records: List[Record] = []
        for t in tables:
            headers = t.col_headers
            for row in t.cells:
                fields = {}
                sku = None
                for ci, cell in enumerate(row):
                    if cell is None or cell == "":
                        continue
                    header = headers[ci] if ci < len(headers) else f"col{ci + 1}"
                    canon = _map_header(header)
                    if canon == "price":
                        amount, currency = _price(cell)
                        fields["price"] = cell
                        if amount is not None:
                            fields["price_amount"] = amount
                        if currency:
                            fields["currency"] = currency
                    elif canon:
                        fields[canon] = cell
                        if canon == "sku":
                            sku = cell
                    else:
                        fields[header] = cell
                if t.title:
                    fields.setdefault("collection", t.title)
                # infer a SKU from a code-like cell if no column named one
                if sku is None:
                    for ci, cell in enumerate(row):
                        if cell and _looks_like_sku(cell) and _map_header(
                            headers[ci] if ci < len(headers) else ""
                        ) not in ("price", "quantity", "weight"):
                            sku = cell
                            break
                records.append(
                    Record(sku=sku, fields=fields, source_page=t.source_page,
                           confidence=t.confidence, reasons=list(t.reasons))
                )
        return records
