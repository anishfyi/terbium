"""Classify embedded images by pixel footprint.

Tiny images are almost always material/care icons (FSC, oiled, varnished). Mid
images are finish swatches. Large images are product or lifestyle photography.
This split drives the vision lane: icons and swatches carry parseable metadata,
photos usually do not.
"""
from __future__ import annotations

ICON_MAX = 64          # < 64x64 px
SWATCH_MAX = 300       # < 300x300 px, else photo


def classify(width: int, height: int) -> str:
    longest = max(width, height)
    if longest < ICON_MAX:
        return "icon"
    if longest < SWATCH_MAX:
        return "swatch"
    return "photo"
