"""Terminal table rendering with a never-crash fallback chain.

unicode box table -> ASCII table -> aligned plain columns -> raw CSV lines
"""
from __future__ import annotations

import csv
import io
import shutil
from typing import List, Sequence


def _column_widths(headers: Sequence[str], rows: Sequence[Sequence]) -> List[int]:
    cols = len(headers)
    w = [len(str(h)) for h in headers]
    for r in rows:
        for i in range(min(cols, len(r))):
            w[i] = max(w[i], len(str(r[i])))
    return w


def _fit_widths(widths: List[int], term: int) -> List[int]:
    cols = len(widths)
    w = list(widths)
    guard = 0
    while sum(w) + 3 * (cols - 1) > term and guard < 10000:
        j = w.index(max(w))
        if w[j] <= 6:
            break
        w[j] -= 1
        guard += 1
    return w


def _cell(s, width: int) -> str:
    s = str(s)
    if len(s) <= width:
        return s
    if width <= 1:
        return s[:width]
    return s[: max(1, width - 1)] + "..."


def _unicode_table(headers: Sequence[str], rows: Sequence[Sequence], widths: List[int]) -> str:
    top = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    lines = [top]
    lines.append("|" + "|".join(f" {str(h).ljust(widths[i])} " for i, h in enumerate(headers)) + "|")
    lines.append(sep)
    for r in rows:
        lines.append("|" + "|".join(
            f" {_cell(r[i] if i < len(r) else '', widths[i]).ljust(widths[i])} "
            for i in range(len(headers))
        ) + "|")
    lines.append(top)
    return "\n".join(lines)


def _ascii_table(headers: Sequence[str], rows: Sequence[Sequence], widths: List[int]) -> str:
    out = [" | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))]
    out.append("-+-".join("-" * w for w in widths))
    for r in rows:
        out.append(" | ".join(_cell(r[i] if i < len(r) else "", widths[i]).ljust(widths[i])
                              for i in range(len(headers))))
    return "\n".join(out)


def _plain_columns(headers: Sequence[str], rows: Sequence[Sequence], widths: List[int]) -> str:
    out = ["  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))]
    for r in rows:
        out.append("  ".join(_cell(r[i] if i < len(r) else "", widths[i]).ljust(widths[i])
                             for i in range(len(headers))))
    return "\n".join(out)


def _raw_csv(headers: Sequence[str], rows: Sequence[Sequence]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(list(r))
    return buf.getvalue()


def render_terminal_table(headers: Sequence[str], rows: Sequence[Sequence],
                          term_width: int = None) -> str:
    """Render a table; never raises."""
    try:
        if not headers:
            return ""
        term = term_width or shutil.get_terminal_size((80, 20)).columns
        widths = _fit_widths(_column_widths(headers, rows), term)
        for renderer in (_unicode_table, _ascii_table, _plain_columns):
            try:
                return renderer(headers, rows, widths)
            except Exception:
                continue
        return _raw_csv(headers, rows)
    except Exception:
        try:
            return _raw_csv(headers or ["col1"], rows or [])
        except Exception:
            return ""
