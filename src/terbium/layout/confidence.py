"""Score how much terbium should trust a reconstructed table.

Honesty is the whole point: a clean, full, well-labelled grid scores high; a
ragged, header-less, sparse one scores low and triggers escalation. terbium
never pretends a shaky parse is solid.
"""
from __future__ import annotations

from typing import List, Tuple

from ..model.table import ExtractedTable


def score_table(table: ExtractedTable) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    conf = 0.98
    n_rows = table.n_rows
    n_cols = table.n_cols or 1
    single_col = n_cols == 1

    generic_headers = all(
        (h or "").startswith("col") and (h or "")[3:].isdigit() for h in table.col_headers
    ) if table.col_headers else True
    if generic_headers and not single_col:
        conf -= 0.14
        reasons.append("no finish/column headers detected")

    if table.title is None:
        conf -= 0.10
        reasons.append("no product title found above the table")

    filled = sum(1 for row in table.cells for v in row if v)
    total = n_rows * n_cols
    fill = filled / total if total else 0.0
    if fill < 0.999 and not single_col:
        # partial fill is genuinely ambiguous: a real gap, or a mis-placed cell
        penalty = round((1.0 - fill) * 0.35, 3)
        conf -= penalty
        reasons.append(f"sparse matrix: {filled}/{total} cells filled")

    # ragged rows: rows whose SKU count differs from the column count
    ragged = sum(1 for row in table.cells if sum(1 for v in row if v) not in (n_cols, 0))
    if ragged and not single_col:
        conf -= min(0.2, 0.05 * ragged)
        reasons.append(f"{ragged} row(s) do not line up with the columns")

    conf = max(0.05, min(1.0, conf))
    table.confidence = conf
    table.reasons = reasons
    return conf, reasons
