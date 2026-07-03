"""Vision lane: read what lives only in the pixels.

Material/care icons (FSC, oiled, varnished) and finish swatches carry metadata
that never appears in the extracted text. This reads them off a rendered page.
Opt-in and standalone - not on the default parse path, which stays deterministic.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from .ai import AI
from .providers import vision_provider

VISION_SYSTEM = (
    "You read document imagery. Identify any material or care icons (e.g. FSC, "
    "oiled, varnished) and any finish/colour swatch labels visible in the image. "
    "Return ONLY JSON: {\"icons\": [<string>...], \"finishes\": [<string>...]}."
)


def read_page(path: str, page_index: int, ai: AI, dpi: int = 130) -> Optional[dict]:
    """Render a PDF page and ask a vision model what its imagery says."""
    provider = vision_provider(ai)
    if provider is None:
        return None
    try:
        from ..documents.pdf import render_page_png

        image = render_page_png(path, page_index, dpi=dpi)
    except Exception:
        return None
    raw = provider.complete("What do the icons and swatches on this page say?", VISION_SYSTEM, "sonnet", image_png=image)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
