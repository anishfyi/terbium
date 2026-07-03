"""Furniture-catalogue schema: the worked example.

Turns a finish x size matrix into one record per article number, with product,
size, finish, and both metric and imperial dimensions parsed out of the row
label. This is the shape the Ethnicraft-style catalogue wants.
"""
from __future__ import annotations

from typing import List, Optional

from ..layout import signals
from ..model.record import Record
from ..model.table import ExtractedTable
from .base import Schema, register_schema


def _dims(row_header: Optional[str]):
    if not row_header:
        return None, None
    dims = signals.find_dimensions(row_header)
    cm = dims[0]["raw"] if dims else None
    inches = signals.find_inches(row_header)
    inch = " x ".join(f'{v}"' for v in inches) if inches else None
    return cm, inch


@register_schema
class FurnitureSchema(Schema):
    name = "furniture"

    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        records: List[Record] = []
        for t in tables:
            for rh, ch, sku in t.iter_cells():
                cm, inch = _dims(rh)
                fields = {
                    "product": t.title,
                    "size": rh,
                    "finish": ch,
                    "dimensions_cm": cm,
                    "dimensions_in": inch,
                }
                if "composition" in t.attributes:
                    fields["composition"] = t.attributes["composition"]
                if "height" in t.attributes:
                    fields["height"] = t.attributes["height"]
                records.append(
                    Record(sku=sku, fields=fields, source_page=t.source_page,
                           confidence=t.confidence, reasons=list(t.reasons))
                )
        return records
