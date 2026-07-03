"""Strip running headers and footers by detecting what repeats at page edges.

The trick that makes this robust: a running header ("furniture 2026", a section
name, a page number) recurs across many pages *at the same vertical band near an
edge*. Mid-page content that happens to repeat (like the axis label
'length x width x height') is deliberately never stripped, so table detection
downstream keeps its anchors.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Callable, List

from ..model.elements import Line, Page
from .lines import cluster_lines

N_BANDS = 12
EDGE_BANDS = {0, 1, N_BANDS - 2, N_BANDS - 1}
_NUM = re.compile(r"\b\d+\b")
_PAGENUM = re.compile(r"^\s*\d{1,4}(?:\s+\d{1,4})?\s*$")


def _norm(text: str) -> str:
    """Drop standalone numbers so 'dining tables 26 27' == 'dining tables 30 31'."""
    return re.sub(r"\s+", " ", _NUM.sub("", text)).strip().lower()


def _band(y: float, height: float) -> int:
    if height <= 0:
        return 0
    return min(N_BANDS - 1, max(0, int((y / height) * N_BANDS)))


def build_stripper(pages: List[Page], min_frac: float = 0.2) -> Callable[[Line, Page], bool]:
    """Return ``is_header(line, page) -> bool`` learned from the whole document."""
    counts: Counter = Counter()
    n = max(1, len(pages))
    for p in pages:
        for ln in cluster_lines(p.words):
            band = _band(ln.y, p.height)
            if band not in EDGE_BANDS:
                continue
            norm = _norm(ln.text)
            if norm:
                counts[(norm, band)] += 1
    threshold = max(3, int(min_frac * n))
    repeated = {k for k, c in counts.items() if c >= threshold and len(k[0]) <= 48}

    def is_header(line: Line, page: Page) -> bool:
        band = _band(line.y, page.height)
        if band not in EDGE_BANDS:
            return False
        text = line.text.strip()
        if _PAGENUM.match(text):
            return True
        return (_norm(text), band) in repeated

    return is_header


def strip_headers(page: Page, is_header: Callable[[Line, Page], bool]) -> List[Line]:
    """Return the page's lines with headers/footers removed."""
    return [ln for ln in cluster_lines(page.words) if not is_header(ln, page)]
