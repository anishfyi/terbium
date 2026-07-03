"""CSV adapter (stdlib).

Sniffs the delimiter and whether a header row exists, tolerates messy encodings,
and hands back a single native table. The easy case, handled honestly.
"""
from __future__ import annotations

import csv as _csv
from typing import List, Optional

from ..model.elements import Page
from ..model.table import ExtractedTable
from .base import DocumentAdapter, register

_MAX_ROWS = 20000


def _read_text(path: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="latin-1", errors="replace", newline="") as f:
        return f.read()


@register
class CsvAdapter(DocumentAdapter):
    extensions = ("csv", "tsv")

    def parse(self, path: str) -> List[Page]:
        text = _read_text(path)
        sample = text[:8192]
        try:
            dialect = _csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except _csv.Error:
            dialect = _csv.excel
            dialect.delimiter = "\t" if path.lower().endswith(".tsv") else ","
        try:
            has_header = _csv.Sniffer().has_header(sample)
        except _csv.Error:
            has_header = True

        rows: List[List[str]] = []
        for i, row in enumerate(_csv.reader(text.splitlines(), dialect)):
            if i >= _MAX_ROWS:
                break
            rows.append([c.strip() for c in row])
        rows = [r for r in rows if any(c for c in r)]
        table = _rows_to_table(rows, has_header)
        page = Page(index=0, width=0, height=0, source_kind="csv", native_tables=[table] if table else [])
        return [page]


def _rows_to_table(rows: List[List[str]], has_header: bool) -> Optional[ExtractedTable]:
    if not rows:
        return None
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    if has_header:
        col_headers = rows[0]
        body = rows[1:]
    else:
        col_headers = [f"col{i + 1}" for i in range(ncol)]
        body = rows
    return ExtractedTable(
        title=None,
        row_headers=[""] * len(body),
        col_headers=[h or f"col{i + 1}" for i, h in enumerate(col_headers)],
        cells=[[(v or None) for v in r] for r in body],
        source_page=0,
        kind="grid",
    )
