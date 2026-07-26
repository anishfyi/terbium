"""Form and key-value extraction by geometry.

Reads label:value pairs from invoices, receipts, and similar layouts:
- colon-terminated labels with same-line values
- label-above-value stacks common in invoices
- left-text / right-amount row pairing (tolerant of dot leaders)
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ..model.elements import Line, Page
from . import signals
from .lines import cluster_lines

_DOT_LEADER = re.compile(r"\.{2,}\s*")
_SAME_LINE_KV = re.compile(
    r"^([A-Za-z][A-Za-z0-9 /&().,'-]{0,48}?):\s*(.+)$"
)
_AMOUNT_TAIL = re.compile(
    r"([$£€₹]?\s*[\d][\d,]*\.?\d*)\s*$"
)


def extract_kv_pairs(page: Page) -> List[Dict[str, str]]:
    """Extract label:value pairs from a page by geometry."""
    lines = cluster_lines(page.words)
    pairs: List[Dict[str, str]] = []
    seen: set = set()

    for ln in lines:
        text = ln.text.strip()
        if not text:
            continue
        m = _SAME_LINE_KV.match(text)
        if m:
            label, value = m.group(1).strip(), m.group(2).strip()
            key = label.lower()
            if key not in seen:
                seen.add(key)
                pairs.append({"label": label, "value": value, "kind": "inline"})

    # label-above-value stacks
    ordered = sorted(lines, key=lambda l: l.y)
    for i, ln in enumerate(ordered):
        label = ln.text.strip().rstrip(":")
        if not label or ":" in label or len(label) > 48:
            continue
        if not label[0].isalpha():
            continue
        if signals.find_amounts(label) or signals.find_dates(label):
            continue
        h = max(8.0, ln.max_size or 12.0)
        for j in range(i + 1, min(i + 4, len(ordered))):
            nxt = ordered[j]
            dy = nxt.y - ln.y
            if dy <= 0 or dy > h * 2.5:
                continue
            if abs(nxt.x0 - ln.x0) > 40:
                continue
            value = nxt.text.strip()
            if not value:
                continue
            key = label.lower()
            if key not in seen:
                seen.add(key)
                pairs.append({"label": label, "value": value, "kind": "stacked"})
            break

    # left-text / right-amount rows
    for ln in lines:
        row = extract_amount_row(ln)
        if row:
            desc, amt = row
            key = f"row:{desc[:30].lower()}"
            if key not in seen:
                seen.add(key)
                pairs.append({"label": desc, "value": amt, "kind": "amount_row"})

    return pairs


def extract_amount_row(line: Line) -> Optional[Tuple[str, str]]:
    """Split a line into description (left) and amount (right), dot-leader tolerant."""
    text = line.text.strip()
    if not text:
        return None
    # try dot leaders first
    parts = _DOT_LEADER.split(text)
    if len(parts) == 2:
        desc, amt = parts[0].strip(), parts[1].strip()
        if signals.find_amounts(amt):
            return desc, amt
    # geometric: words on the right that look like amounts
    if len(line.words) < 2:
        return None
    words = sorted(line.words, key=lambda w: w.x0)
    for split in range(len(words) - 1, 0, -1):
        right_text = " ".join(w.text for w in words[split:])
        if signals.find_amounts(right_text):
            left_text = " ".join(w.text for w in words[:split]).strip()
            if left_text and len(left_text) >= 2:
                return left_text, right_text.strip()
    m = _AMOUNT_TAIL.search(text)
    if m:
        amt = m.group(1)
        desc = text[: m.start()].strip(" .:-")
        if desc and len(desc) >= 2:
            return desc, amt
    return None


def pairs_to_fields(pairs: List[Dict[str, str]]) -> Dict[str, str]:
    """Flatten extracted pairs into a simple field dict."""
    out: Dict[str, str] = {}
    for i, p in enumerate(pairs):
        key = p["label"].lower().replace(" ", "_")
        if key in out:
            key = f"{key}_{i}"
        out[key] = p["value"]
    return out
