"""Low-level geometric elements produced by document adapters.

Everything downstream (de-heading, grid reconstruction, confidence) reasons
over these. They are format-agnostic: a PDF word, a PPTX text run, and an XLSX
cell all normalize into the same shapes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Word:
    """A positioned run of text with its bounding box in page coordinates."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float = 0.0          # font size, when the source exposes it (PDF/PPTX)
    bold: bool = False

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0


@dataclass
class Line:
    """A horizontal run of words sharing a baseline."""
    words: List[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words).strip()

    @property
    def y(self) -> float:
        return sum(w.cy for w in self.words) / len(self.words) if self.words else 0.0

    @property
    def x0(self) -> float:
        return min((w.x0 for w in self.words), default=0.0)

    @property
    def max_size(self) -> float:
        return max((w.size for w in self.words), default=0.0)

    @property
    def any_bold(self) -> bool:
        return any(w.bold for w in self.words)


@dataclass
class ImageRef:
    """An image embedded on a page, classified by pixel footprint."""
    page: int
    width: int
    height: int
    kind: str = "photo"        # icon | swatch | photo
    bbox: Optional[Tuple[float, float, float, float]] = None
    xref: Optional[int] = None


@dataclass
class Page:
    """A single page/slide/sheet, normalized across formats."""
    index: int                 # 0-based
    width: float
    height: float
    words: List[Word] = field(default_factory=list)
    images: List[ImageRef] = field(default_factory=list)
    source_kind: str = "pdf"   # pdf | pptx | xlsx | csv
    # Some adapters (PPTX tables, XLSX, CSV) can hand us a native grid directly,
    # so the geometric engine does not have to reconstruct one.
    native_tables: List["object"] = field(default_factory=list)

    @property
    def median_size(self) -> float:
        sizes = sorted(w.size for w in self.words if w.size > 0)
        if not sizes:
            return 0.0
        return sizes[len(sizes) // 2]
