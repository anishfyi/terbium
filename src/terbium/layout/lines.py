"""Cluster positioned words into lines by shared baseline.

The single most useful primitive in the whole engine: PDF text extraction gives
you words with (x, y); a line is a run of words with nearly-equal y, sorted by x.
"""
from __future__ import annotations

from typing import List

from ..model.elements import Line, Word


def cluster_lines(words: List[Word], y_tol: float = 3.0) -> List[Line]:
    """Group words into lines. ``y_tol`` is in page points."""
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (round(w.cy, 1), w.x0))
    lines: List[List[Word]] = []
    current: List[Word] = [ordered[0]]
    ref_y = ordered[0].cy
    for w in ordered[1:]:
        if abs(w.cy - ref_y) <= y_tol:
            current.append(w)
            # running mean keeps drift-resistant baseline
            ref_y = sum(x.cy for x in current) / len(current)
        else:
            lines.append(current)
            current = [w]
            ref_y = w.cy
    lines.append(current)
    # sort each line left-to-right, and lines top-to-bottom
    out = [Line(words=sorted(ws, key=lambda w: w.x0)) for ws in lines]
    out.sort(key=lambda ln: ln.y)
    return out
