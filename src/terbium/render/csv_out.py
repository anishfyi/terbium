"""Generic CSV output for any schema: union of field keys as columns, stable order."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional, Sequence


def _collect_columns(rows: Sequence[Dict[str, Any]]) -> List[str]:
    keys: List[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    return keys


def records_to_csv(rows: Sequence[Dict[str, Any]], extra_cols: Sequence[str] = ("sku", "confidence")) -> str:
    """Serialize record dicts to CSV text."""
    field_keys = _collect_columns(rows)
    for c in extra_cols:
        if c not in field_keys:
            field_keys.insert(0, c)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(field_keys)
    for row in rows:
        w.writerow([row.get(k, "") for k in field_keys])
    return buf.getvalue()


def to_csv(records, path: Optional[str] = None) -> str:
    """Write any terbium records (Record objects or dicts) to CSV."""
    rows: List[Dict[str, Any]] = []
    for r in records:
        if hasattr(r, "fields"):
            row: Dict[str, Any] = {"sku": getattr(r, "sku", "") or "",
                                   "confidence": f"{getattr(r, 'confidence', 0):.2f}"}
            row.update(r.fields)
            rows.append(row)
        else:
            rows.append(dict(r))
    text = records_to_csv(rows)
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return text
