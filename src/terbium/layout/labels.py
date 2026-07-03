"""Extract label/name grids from visual pages that have no structured table.

Lookbooks and slide decks are not matrices: they are a grid of product photos
with a name under each, grouped by a collection title. terbium was over-fit to
the dimension x finish matrix and returned nothing here.

To read them cleanly this has to do two things a naive line reader cannot:
- segment each row horizontally, so four names on one baseline become four
  labels, not one run;
- stitch a wrapped label ("Meadow Bedside" over "Table") back into one name.

It only fires on genuine label grids: a page with several images and names in at
least two columns. A prose page with one hero image escalates to vision instead.
"""
from __future__ import annotations

from typing import List, Optional

from ..model.elements import Line, Page
from ..model.table import ExtractedTable
from .signals import find_skus, has_dimension, is_composition

MAX_WORDS = 8
MAX_CHARS = 48
MIN_IMAGES = 3          # a lookbook page has many product photos
MIN_NAMES = 3
GAP = 24.0              # horizontal gap (pt) that separates two labels on a row


def _cx(line: Line) -> float:
    return sum(w.cx for w in line.words) / len(line.words) if line.words else 0.0


def _segment_row(line: Line) -> List[Line]:
    """Split a baseline into separate labels wherever a wide horizontal gap sits."""
    words = sorted(line.words, key=lambda w: w.x0)
    if len(words) <= 1:
        return [line]
    segs: List[List] = [[words[0]]]
    for w in words[1:]:
        if w.x0 - segs[-1][-1].x1 > GAP:
            segs.append([w])
        else:
            segs[-1].append(w)
    return [Line(words=s) for s in segs]


def _is_label(line: Line) -> bool:
    t = line.text.strip()
    if not t or len(line.words) > MAX_WORDS or len(t) > MAX_CHARS:
        return False
    if has_dimension(t) or find_skus(t) or is_composition(t):
        return False
    return sum(c.isalpha() for c in t) >= 2


def _xrange(line: Line):
    return min(w.x0 for w in line.words), max(w.x1 for w in line.words)


def _merge_wrapped(cands: List[Line]) -> List[dict]:
    """Merge a wrapped label (one name spilling onto two lines) into one name.

    Uses horizontal overlap, not centre distance, so a short continuation like
    'Table' under 'Meadow Bedside' still attaches even though its centre shifts.
    """
    used = [False] * len(cands)
    order = sorted(range(len(cands)), key=lambda i: (cands[i].y, _cx(cands[i])))
    out: List[dict] = []
    for i in order:
        if used[i]:
            continue
        g = [cands[i]]
        used[i] = True
        h = max(8.0, cands[i].max_size or 12.0)
        changed = True
        while changed:
            changed = False
            gx0, gx1 = _xrange(g[-1])
            for j in order:
                if used[j]:
                    continue
                x0, x1 = _xrange(cands[j])
                dy = cands[j].y - g[-1].y
                overlap = min(gx1, x1) - max(gx0, x0)
                if overlap > -8 and 0 < dy < h * 3.0:
                    g.append(cands[j])
                    used[j] = True
                    changed = True
        text = " ".join(ln.text.strip() for ln in g).strip()
        if len(g) <= 3 and len(text) <= MAX_CHARS:
            out.append({"name": text, "cx": _cx(g[0]), "y": g[0].y, "size": g[0].max_size})
    return out


def _pick_collection(items: List[dict], page: Page) -> Optional[str]:
    med = page.median_size
    if med > 0:
        big = [it for it in items if it["size"] >= 1.18 * med]
        if big:
            return min(big, key=lambda it: it["y"])["name"]
    ordered = sorted(items, key=lambda it: it["y"])
    if len(ordered) >= 2 and ordered[1]["y"] - ordered[0]["y"] > 2 * (med or 14):
        return ordered[0]["name"]              # a title set well above the grid
    return None


def extract_labels(lines: List[Line], page: Page) -> Optional[ExtractedTable]:
    if len(page.images) < MIN_IMAGES:
        return None
    cands: List[Line] = []
    for ln in lines:
        for seg in _segment_row(ln):
            if _is_label(seg):
                cands.append(seg)
    if len(cands) < MIN_NAMES:
        return None

    items = _merge_wrapped(cands)
    collection = _pick_collection(items, page)
    names = [it for it in items if it["name"] != collection]
    if len(names) < MIN_NAMES:
        return None

    width = page.width or 1000.0
    n_cols = len({round(it["cx"] / (width / 8)) for it in names})
    if n_cols < 2:
        return None                            # a single column is prose, not a grid

    return ExtractedTable(
        title=collection,
        row_headers=[""] * len(names),
        col_headers=["name"],
        cells=[[it["name"]] for it in names],
        source_page=page.index,
        kind="labels",
        confidence=0.82,
        reasons=["names recovered from a visual label grid (no structured table)"],
    )
