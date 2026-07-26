"""Typed signal detection: the regexes that turn raw tokens into meaning.

These are deliberately conservative. A signal firing is evidence; the grid and
confidence layers decide what to trust.
"""
from __future__ import annotations

import re
from typing import List, Optional, Pattern, Sequence

# SKU patterns: 5-digit article, dashed alphanumerics, general codes.
# Word-boundaried so they do not match inside longer runs.
SKU_PATTERNS: Sequence[Pattern] = (
    re.compile(r"(?<!\d)(\d{5})(?!\d)"),                          # 5-digit article
    re.compile(r"\b([A-Z]{2,6}-\d{2,6})\b"),                       # MRP-962, RG-1001
    re.compile(r"\b([A-Za-z]{1,4}\d{3,8}[A-Za-z]?)\b"),           # BG22, HW602
    re.compile(r"\b(\d{4,8}[A-Za-z]{1,3})\b"),                    # 20156A
)
# Backwards-compatible alias
SKU_RE = SKU_PATTERNS[0]

# Price/year/rate rejections when matching SKU-like tokens
_YEAR_RE = re.compile(r"^(18|19|20)\d{2}$")
_RATE_RE = re.compile(r"^\d+(?:\.\d+)?/[A-Za-z]{1,6}\.?$")
_PRICE_ONLY_RE = re.compile(r"^[$£€₹]?\s*[\d,]+\.?\d*$")

# Amounts with currency symbols or codes
AMOUNT_RE = re.compile(
    r"(?:[$£€₹]|USD|GBP|EUR|INR|Rs\.?)\s*[\d][\d,]*\.?\d*"
    r"|[\d][\d,]*\.?\d*\s*(?:USD|GBP|EUR|INR)",
    re.IGNORECASE,
)

# Common date formats
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)

INVOICE_RE = re.compile(
    r"\b(?:invoice|inv|receipt|bill|po|purchase order|quote)\s*#?\s*:?\s*([A-Z0-9][-A-Z0-9]{2,20})\b",
    re.IGNORECASE,
)
TAX_ID_RE = re.compile(
    r"\b(?:vat|gst|tax id|ein|abn)\s*#?\s*:?\s*([A-Z0-9][-A-Z0-9]{4,20})\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s<>\"']*")

# Dimensions: "240 × 110 x 76 cm", "200 x 100 cm", with the metric block first.
_MULT = r"[×xX*]"
DIM_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*" + _MULT + r"\s*(\d+(?:[.,]\d+)?)"
    r"(?:\s*" + _MULT + r"\s*(\d+(?:[.,]\d+)?))?\s*(cm|mm|m)\b",
    re.IGNORECASE,
)

INCH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[\"”]")

COMPOSITION_RE = re.compile(r"\b(\d{1,3})\s*%\s*[a-zA-Z]")

MARKER_RE = re.compile(r"\((new)\*?\)|(?<!\w)\*(?!\w)", re.IGNORECASE)


def _reject_sku_token(tok: str) -> bool:
    t = tok.strip(".,;:()[]")
    if re.fullmatch(r"\d{5}", t):
        return False
    if _YEAR_RE.match(t) or _RATE_RE.match(t):
        return True
    if _PRICE_ONLY_RE.match(t):
        return True
    return False


def find_skus(text: str, pattern: Optional[re.Pattern] = None) -> List[str]:
    if pattern is not None:
        return [m for m in pattern.findall(text) if not _reject_sku_token(m)]
    found: List[str] = []
    for rx in SKU_PATTERNS:
        for m in rx.findall(text):
            tok = m if isinstance(m, str) else m[0]
            if not _reject_sku_token(tok) and tok not in found:
                found.append(tok)
    return found


def looks_like_sku_token(tok: str) -> bool:
    """True when a token matches any SKU pattern and passes rejection filters."""
    t = tok.strip(".,;:()[]")
    if not t or _reject_sku_token(t):
        return False
    if re.fullmatch(r"\d{5}", t):
        return True
    for rx in SKU_PATTERNS:
        if rx.fullmatch(t):
            return True
    return bool(find_skus(t))


def find_amounts(text: str) -> List[str]:
    return [m.group(0) for m in AMOUNT_RE.finditer(text)]


def find_dates(text: str) -> List[str]:
    return [m.group(0) for m in DATE_RE.finditer(text)]


def find_invoice_numbers(text: str) -> List[str]:
    return [m.group(1) for m in INVOICE_RE.finditer(text)]


def find_tax_ids(text: str) -> List[str]:
    return [m.group(1) for m in TAX_ID_RE.finditer(text)]


def find_emails(text: str) -> List[str]:
    return EMAIL_RE.findall(text)


def find_phones(text: str) -> List[str]:
    return PHONE_RE.findall(text)


def find_urls(text: str) -> List[str]:
    return URL_RE.findall(text)


def find_dimensions(text: str) -> List[dict]:
    """Return structured dimension dicts found in text."""
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
