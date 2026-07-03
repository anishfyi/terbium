"""Content-agnostic table reconstruction.

This is the generic engine: it finds tables in any PDF by geometry alone, making
no assumption about what the cells contain. A run of consecutive lines that share
the same column structure is a table; the first row is the header; every cell is
placed by x-alignment. Works on a financial table, a spec sheet, a schedule, or a
furniture matrix - the detector does not care what the numbers mean.

The furniture cross-tab is just a special case (its first column is a size axis,
its other columns are finishes), which the furniture schema interprets on top of
the generic grid produced here.
"""
from __future__ import annotations

from collections import Counter
from typing import List, Optional

from ..model.elements import Line, Page
from ..model.table import ExtractedTable
from .grid import _assign_column, _split_positions
from .labels import _cx, _segment_row


def is_data_table(t: ExtractedTable) -> bool:
    """True when a table carries real data (numbers/codes), not just prose names.

    Distinguishes a financial or spec table from a lookbook grid of product
    names, which should go to label extraction instead.
    """
    cells = [c for row in t.cells for c in row if c]
    if not cells:
        return False
    with_digit = sum(1 for c in cells if any(ch.isdigit() for ch in c))
    return with_digit / len(cells) >= 0.15


def _median_gap(lines: List[Line]) -> float:
    ys = sorted(ln.y for ln in lines)
    gaps = [b - a for a, b in zip(ys, ys[1:]) if b - a > 0.5]
    return sorted(gaps)[len(gaps) // 2] if gaps else 12.0


def _title_above(first: Line, lines: List[Line], page: Page) -> Optional[str]:
    """The nearest short line just above a table - its caption or product name."""
    best = None
    for ln in lines:
        if ln.y < first.y and (first.y - ln.y) < 70:
            if best is None or ln.y > best.y:
                best = ln
    if best is not None and best.words and len(best.words) <= 8:
        return best.text.strip() or None
    return None


def detect_tables(lines: List[Line], page: Page) -> List[ExtractedTable]:
    if not lines:
        return []
    gap_thresh = max(26.0, 2.4 * _median_gap(lines))
    seg = [(ln, _segment_row(ln)) for ln in lines]

    # group consecutive multi-cell rows into blocks; a single-cell line (a title
    # or a paragraph) or a big vertical gap ends the current block.
    blocks: List[list] = []
    cur: list = []
    prev_y = None
    for ln, cells in seg:
        if len(cells) >= 2:
            if prev_y is not None and (ln.y - prev_y) > gap_thresh and len(cur) >= 2:
                blocks.append(cur)
                cur = []
            elif prev_y is not None and (ln.y - prev_y) > gap_thresh:
                cur = []
            cur.append((ln, cells))
            prev_y = ln.y
        else:
            if len(cur) >= 2:
                blocks.append(cur)
            cur = []
            prev_y = None
    if len(cur) >= 2:
        blocks.append(cur)

    tables = []
    for block in blocks:
        t = _build(block, lines, page)
        if t is not None:
            tables.append(t)
    return tables


def _build(block: list, all_lines: List[Line], page: Page) -> Optional[ExtractedTable]:
    ncol = Counter(len(cells) for _, cells in block).most_common(1)[0][0]
    if ncol < 2:
        return None
    centers = [_cx(c) for _, cells in block for c in cells]
    anchors = _split_positions(centers, ncol)

    grid: List[List[Optional[str]]] = []
    for _, cells in block:
        row: List[Optional[str]] = [None] * ncol
        for c in cells:
            ci = _assign_column(_cx(c), anchors)
            txt = c.text.strip()
            row[ci] = (row[ci] + " " + txt).strip() if row[ci] else txt
        grid.append(row)

    col_headers = [h or f"col{i + 1}" for i, h in enumerate(grid[0])]
    body = grid[1:]
    if not body:
        return None

    # reject multi-column prose (an intro paragraph laid out in columns): real
    # table cells are short, prose cells are sentence fragments.
    wc = sorted(len(c.split()) for row in body for c in row if c)
    if wc and wc[len(wc) // 2] > 5:
        return None
    return ExtractedTable(
        title=_title_above(block[0][0], all_lines, page),
        row_headers=[""] * len(body),
        col_headers=col_headers,
        cells=body,
        source_page=page.index,
        kind="grid",
    )
