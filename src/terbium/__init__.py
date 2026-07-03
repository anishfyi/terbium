"""terbium - a god-level algorithmic multi-file parser that scores its own
confidence and only reaches for AI when it is genuinely stuck.

    import terbium
    doc = terbium.parse("catalogue.pdf")
    print(doc.stats)
    for r in doc.records:
        print(r.sku, r.fields)
"""
from __future__ import annotations

from .api import parse, supported_extensions, DEFAULT_THRESHOLD
from .extract import export_images
from .harness import AI
from .harness.vision import read_page as read_vision
from .model.document import ParsedDocument, Stats
from .model.record import Record
from .model.table import ExtractedTable

__version__ = "0.5.0"

__all__ = [
    "parse",
    "export_images",
    "AI",
    "read_vision",
    "supported_extensions",
    "ParsedDocument",
    "Record",
    "ExtractedTable",
    "Stats",
    "__version__",
]
