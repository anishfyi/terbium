"""Split a two-page spread at its gutter.

Print catalogues are laid out as spreads: one PDF page is really two pages side
by side. Without splitting, a product on the left bleeds into the product on the
right (shared title lines, merged columns). We detect the empty vertical gutter
near the centre and cut there - unless a table genuinely spans it.
"""
from __future__ import annotations

from typing import List

from ..model.elements import Page, Word


def split_columns(page: Page) -> List[List[Word]]:
    words = page.words
    if not words:
        return [words]
    # only landscape pages are plausible spreads
    if page.width <= page.height * 1.15:
        return [words]
    w = page.width
    lo, hi = 0.46 * w, 0.54 * w
    crossing = [x for x in words if lo < x.cx < hi]
    if len(crossing) > max(4, 0.06 * len(words)):
        return [words]          # content spans the centre - not a clean spread
    g = w / 2.0
    left = [x for x in words if x.cx < g]
    right = [x for x in words if x.cx >= g]
    if not left or not right:
        return [words]
    return [left, right]
