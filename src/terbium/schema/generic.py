"""The default schema: works for any table without domain knowledge.

- grid tables (XLSX/CSV/PPTX): one record per body row, columns become fields.
- matrix tables (a PDF finish x size grid): one record per filled cell.
"""
from __future__ import annotations

import re
from typing import List, Optional

from ..model.record import Record
from ..model.table import ExtractedTable
from .base import Schema, register_schema

_CODE_RE = re.compile(r"^[A-Za-z0-9._/-]{3,16}$")


def _as_sku(value: Optional[str]) -> Optional[str]:
    """Treat a compact, digit-bearing code as a SKU; leave prose alone."""
    if not value:
        return None
    v = value.strip()
    if _CODE_RE.match(v) and any(c.isdigit() for c in v):
        return v
    return None


@register_schema
class GenericSchema(Schema):
    name = "generic"

    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        records: List[Record] = []
        for t in tables:
            if t.kind == "grid":
                records.extend(self._grid_records(t))
            else:
                records.extend(self._cell_records(t))
        return records

    def _grid_records(self, t: ExtractedTable) -> List[Record]:
        out: List[Record] = []
        for ri, row in enumerate(t.cells):
            fields = {}
            row_label = t.row_headers[ri] if ri < len(t.row_headers) else None
            if row_label:
                fields["row_label"] = row_label
            for ci, val in enumerate(row):
                key = t.col_headers[ci] if ci < len(t.col_headers) else f"col{ci + 1}"
                fields[key] = val
            if t.title:
                fields["title"] = t.title
            fields.update(t.attributes)
            sku = _as_sku(row_label)
            if sku is None:
                for val in row:
                    sku = _as_sku(val)
                    if sku:
                        break
            out.append(
                Record(sku=sku, fields=fields, source_page=t.source_page,
                       confidence=t.confidence, reasons=list(t.reasons))
            )
        return out

    def _cell_records(self, t: ExtractedTable) -> List[Record]:
        out: List[Record] = []
        for rh, ch, val in t.iter_cells():
            fields = {}
            if t.title:
                fields["title"] = t.title
            if rh:
                fields["row"] = rh
            if ch:
                fields["column"] = ch
            fields.update(t.attributes)
            out.append(
                Record(sku=val, fields=fields, source_page=t.source_page,
                       confidence=t.confidence, reasons=list(t.reasons))
            )
        return out
