"""Typed signal detection: the regexes that turn raw tokens into meaning.

These are deliberately conservative. A signal firing is evidence; the grid and
confidence layers decide what to trust.
"""
from __future__ import annotations

import re
from typing import List, Optional

# A 5-digit article number, as used across the grounding catalogue. Tunable via
# parse(sku_pattern=...). Word-boundaried so it does not match inside longer runs.
SKU_RE = re.compile(r"(?<!\d)(\d{5})(?!\d)")

# Dimensions: "240 × 110 x 76 cm", "200 x 100 cm", with the metric block first.
# The unicode multiplication sign and the ascii x/X are both used in the wild.
_MULT = r"[×xX*]"
DIM_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*" + _MULT + r"\s*(\d+(?:[.,]\d+)?)"
    r"(?:\s*" + _MULT + r"\s*(\d+(?:[.,]\d+)?))?\s*(cm|mm|m)\b",
    re.IGNORECASE,
)

# Imperial companion, usually after a pipe: 94.5" x 43.5" x 30"
INCH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[\"”]")

# Material composition: 78% polyacrylic, 20% polyester, 2% viscose
COMPOSITION_RE = re.compile(r"\b(\d{1,3})\s*%\s*[a-zA-Z]")

# Novelty / footnote markers
MARKER_RE = re.compile(r"\((new)\*?\)|(?<!\w)\*(?!\w)", re.IGNORECASE)


def find_skus(text: str, pattern: Optional[re.Pattern] = None) -> List[str]:
    rx = pattern or SKU_RE
    return rx.findall(text)


def find_dimensions(text: str) -> List[dict]:
    """Return structured dimension dicts found in text.

    Each: {"cm": "240 x 110 x 76", "unit": "cm", "raw": <match>, "inch": [...]}.
    """
    out: List[dict] = []
    for m in DIM_RE.finditer(text):
        parts = [p for p in (m.group(1), m.group(2), m.group(3)) if p]
        out.append(
            {
                "values": [float(p.replace(",", ".")) for p in parts],
                "unit": m.group(4).lower(),
                "raw": m.group(0).strip(),
            }
        )
    return out


def find_inches(text: str) -> List[float]:
    return [float(m.group(1)) for m in INCH_RE.finditer(text)]


def is_composition(text: str) -> bool:
    return bool(COMPOSITION_RE.search(text))


def has_dimension(text: str) -> bool:
    return bool(DIM_RE.search(text))


def markers(text: str) -> List[str]:
    found = []
    for m in MARKER_RE.finditer(text):
        found.append("new" if m.group(1) else "*")
    return found


def looks_like_axis_label(text: str) -> bool:
    """A dimension-axis header line, e.g. 'length x width x height'."""
    t = text.lower()
    axis_words = ("length", "width", "height", "depth", "diameter", "round", "seat")
    hits = sum(1 for w in axis_words if w in t)
    return hits >= 2 and not has_dimension(text)
