"""The intermediate representation every source collapses into.

A reconstructed 2-D table: row headers down the side, column headers across the
top, and cells in the middle. A furniture matrix is exactly this (rows = size,
cols = finish, cells = article numbers), and so is an XLSX sheet or a CSV. The
schema layer turns these into typed records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExtractedTable:
    title: Optional[str]                 # nearest product/section title, if any
    row_headers: List[str]               # one per data row (e.g. dimension strings)
    col_headers: List[str]               # one per column (e.g. finish names)
    cells: List[List[Optional[str]]]     # cells[row][col]
    source_page: int
    kind: str = "matrix"                 # matrix | grid | list
    attributes: dict = field(default_factory=dict)   # shared attrs (composition, height)
    confidence: float = 1.0
    reasons: List[str] = field(default_factory=list)
    origin: str = "algorithmic"                       # "algorithmic" | "ai"

    @property
    def n_rows(self) -> int:
        return len(self.cells)

    @property
    def n_cols(self) -> int:
        return len(self.col_headers) if self.col_headers else (
            max((len(r) for r in self.cells), default=0)
        )

    def iter_cells(self):
        """Yield (row_header, col_header, value) for every non-empty cell."""
        for ri, row in enumerate(self.cells):
            rh = self.row_headers[ri] if ri < len(self.row_headers) else None
            for ci, val in enumerate(row):
                if val is None or val == "":
                    continue
                ch = self.col_headers[ci] if ci < len(self.col_headers) else None
                yield rh, ch, val
