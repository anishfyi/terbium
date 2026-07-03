"""Reconstruct 2-D tables from word geometry.

This is the part that earns the "god-level algorithmic" claim. Given a page's
de-headed lines, it segments products, finds each product's column headers
(finishes) and row headers (sizes), and places every article number into its
cell by x-alignment. No AI. When the geometry is clean, confidence is high; when
it is ragged, confidence drops and the document escalates.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ..model.elements import Line, Page, Word
from ..model.table import ExtractedTable
from . import signals

# line roles
TITLE, AXIS, DATA, ATTR, OTHER = "title", "axis", "data", "attr", "other"


def _classify(line: Line, page: Page) -> str:
    text = line.text
    if not text:
        return OTHER
    has_dim = signals.has_dimension(text)
    has_sku = bool(signals.find_skus(text))
    if signals.looks_like_axis_label(text):
        return AXIS
    if has_dim and has_sku:
        return DATA
    if has_dim and not has_sku:
        # a lone size line ("table height: 76 cm") is a shared attribute
        return ATTR if ("height" in text.lower() or len(text) < 24) else DATA
    if signals.is_composition(text) or text.lower().startswith(("upholstery", "material")):
        return ATTR
    # title heuristic: visually larger or bold, short, no numbers-heavy content
    med = page.median_size
    big = med > 0 and line.max_size >= 1.12 * med
    short = len(line.words) <= 6
    if (big or line.any_bold) and short and not has_sku and not has_dim:
        return TITLE
    return OTHER


def _split_positions(centers: List[float], k: int) -> List[Tuple[float, float]]:
    """Cluster 1-D x-centers into k groups by splitting at the k-1 largest gaps.

    Returns [(lo, hi)] ranges per column, left to right.
    """
    if k <= 1 or len(centers) <= 1:
        lo, hi = (min(centers), max(centers)) if centers else (0.0, 0.0)
        return [(lo - 1e6, hi + 1e6)]
    xs = sorted(centers)
    gaps = sorted(
        ((xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)),
        reverse=True,
    )
    cut_after = sorted(i for _, i in gaps[: k - 1])
    ranges: List[Tuple[float, float]] = []
    start = 0
    bounds = cut_after + [len(xs) - 1]
    for b in bounds:
        seg = xs[start : b + 1]
        mid_lo = seg[0]
        mid_hi = seg[-1]
        ranges.append((mid_lo, mid_hi))
        start = b + 1
    # widen ranges to midpoints between neighbours so assignment covers gaps
    widened: List[Tuple[float, float]] = []
    for i, (lo, hi) in enumerate(ranges):
        left = -1e6 if i == 0 else (ranges[i - 1][1] + lo) / 2
        right = 1e6 if i == len(ranges) - 1 else (hi + ranges[i + 1][0]) / 2
        widened.append((left, right))
    return widened


def _row_header(line: Line) -> str:
    """The dimension portion of a data row, used as the row label."""
    dims = signals.find_dimensions(line.text)
    if dims:
        return dims[0]["raw"]
    # fall back to text minus the SKU tokens
    skus = set(signals.find_skus(line.text))
    return " ".join(w.text for w in line.words if w.text not in skus).strip()


def _row_cells(line: Line) -> List[Word]:
    """The SKU words in a data row, with their positions preserved."""
    return [w for w in line.words if signals.find_skus(w.text)]


def _column_labels(axis_line: Optional[Line], anchors: List[Tuple[float, float]]) -> List[str]:
    """Finish names from the axis line, grouped into the reconstructed columns."""
    if axis_line is None:
        return [f"col{i + 1}" for i in range(len(anchors))]
    # words after the last axis-vocabulary word are the finish/column names
    axis_vocab = ("length", "width", "height", "depth", "diameter", "round", "seat", "x", "×")
    last_axis_idx = -1
    for i, w in enumerate(axis_line.words):
        if w.text.lower() in axis_vocab:
            last_axis_idx = i
    finish_words = axis_line.words[last_axis_idx + 1 :]
    if not finish_words:
        return [f"col{i + 1}" for i in range(len(anchors))]
    labels = ["" for _ in anchors]
    for w in finish_words:
        ci = _assign_column(w.cx, anchors)
        labels[ci] = (labels[ci] + " " + w.text).strip()
    for i, lab in enumerate(labels):
        if not lab:
            labels[i] = f"col{i + 1}"
    return labels


def _assign_column(cx: float, anchors: List[Tuple[float, float]]) -> int:
    for i, (lo, hi) in enumerate(anchors):
        if lo <= cx <= hi:
            return i
    # nearest by centre if it falls outside all ranges
    centres = [(lo + hi) / 2 for lo, hi in anchors]
    return min(range(len(centres)), key=lambda i: abs(centres[i] - cx))


def _build_table(
    title: Optional[str],
    axis_line: Optional[Line],
    data_rows: List[Line],
    attrs: List[str],
    page_index: int,
) -> Optional[ExtractedTable]:
    if not data_rows:
        return None
    # expected column count = most common SKU-per-row count (robust to a missing variant)
    counts = [len(_row_cells(r)) for r in data_rows]
    k = max(counts) if counts else 0
    if k == 0:
        return None
    all_centers = [w.cx for r in data_rows for w in _row_cells(r)]
    anchors = _split_positions(all_centers, k)
    col_headers = _column_labels(axis_line, anchors)

    row_headers: List[str] = []
    cells: List[List[Optional[str]]] = []
    for r in data_rows:
        row_headers.append(_row_header(r))
        row = [None] * k
        for w in _row_cells(r):
            ci = _assign_column(w.cx, anchors)
            sku = signals.find_skus(w.text)[0]
            if row[ci] is None:
                row[ci] = sku
            else:
                # collision: two SKUs claim one column -> place in first free slot
                for j in range(k):
                    if row[j] is None:
                        row[j] = sku
                        break
        cells.append(row)

    attributes = {}
    for a in attrs:
        if signals.is_composition(a):
            attributes.setdefault("composition", a)
        elif "height" in a.lower():
            attributes.setdefault("height", a)
        else:
            attributes.setdefault("note", a)

    return ExtractedTable(
        title=title,
        row_headers=row_headers,
        col_headers=col_headers,
        cells=cells,
        source_page=page_index,
        kind="matrix" if k > 1 else "list",
        attributes=attributes,
    )


def extract_tables(lines: List[Line], page: Page) -> List[ExtractedTable]:
    """Segment a page into product tables via a small state machine."""
    tables: List[ExtractedTable] = []
    pending_title: Optional[str] = None
    axis_line: Optional[Line] = None
    data_rows: List[Line] = []
    attrs: List[str] = []

    def flush():
        nonlocal axis_line, data_rows, attrs, pending_title
        t = _build_table(pending_title, axis_line, data_rows, attrs, page.index)
        if t is not None:
            tables.append(t)
        axis_line, data_rows, attrs = None, [], []

    for ln in lines:
        role = _classify(ln, page)
        if role == TITLE:
            if data_rows:
                flush()
            pending_title = ln.text
        elif role == AXIS:
            if data_rows:
                flush()
            axis_line = ln
        elif role == DATA:
            data_rows.append(ln)
        elif role == ATTR:
            if data_rows:
                attrs.append(ln.text)
        else:
            continue
    if data_rows:
        flush()
    return tables
