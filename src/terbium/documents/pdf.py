"""PDF adapter (PyMuPDF).

Produces token-level words with positions AND font sizes - the two inputs the
geometry engine needs to rebuild columns, rows, and titles. It also enumerates
embedded images with pixel dimensions so they can be classified, and can render
a page to PNG for the vision lane.
"""
from __future__ import annotations

from typing import List

import fitz  # PyMuPDF

from ..layout.images import classify
from ..model.elements import ImageRef, Page, Word
from .base import DocumentAdapter, register

_BOLD_FLAG = 1 << 4


def _span_words(span: dict) -> List[Word]:
    """Split a span into whitespace tokens, distributing x by character offset.

    Span geometry is exact; per-token x is interpolated across the span box.
    Because catalogue article numbers are fixed-width digits, this places SKU
    cells accurately enough to align them into columns.
    """
    text = span.get("text", "")
    if not text.strip():
        return []
    x0, y0, x1, y1 = span["bbox"]
    size = float(span.get("size", 0.0))
    font = str(span.get("font", "")).lower()
    bold = bool(span.get("flags", 0) & _BOLD_FLAG) or "bold" in font
    width = x1 - x0
    n = len(text)
    words: List[Word] = []
    idx = 0
    for tok in text.split():
        start = text.index(tok, idx)
        end = start + len(tok)
        idx = end
        wx0 = x0 + width * (start / n) if n else x0
        wx1 = x0 + width * (end / n) if n else x1
        words.append(Word(text=tok, x0=wx0, y0=y0, x1=wx1, y1=y1, size=size, bold=bold))
    return words


@register
class PdfAdapter(DocumentAdapter):
    extensions = ("pdf",)

    def parse(self, path: str) -> List[Page]:
        pages: List[Page] = []
        with fitz.open(path) as doc:
            for i, page in enumerate(doc):
                rect = page.rect
                words: List[Word] = []
                data = page.get_text("dict")
                for block in data.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            words.extend(_span_words(span))
                images: List[ImageRef] = []
                try:
                    for info in page.get_image_info(xrefs=True):
                        w = int(info.get("width", 0))
                        h = int(info.get("height", 0))
                        if w and h:
                            images.append(
                                ImageRef(
                                    page=i,
                                    width=w,
                                    height=h,
                                    kind=classify(w, h),
                                    bbox=tuple(info.get("bbox")) if info.get("bbox") else None,
                                    xref=info.get("xref"),
                                )
                            )
                except Exception:
                    pass
                pages.append(
                    Page(
                        index=i,
                        width=rect.width,
                        height=rect.height,
                        words=words,
                        images=images,
                        source_kind="pdf",
                    )
                )
        return pages


def render_page_png(path: str, index: int, dpi: int = 120) -> bytes:
    """Render one page to PNG bytes (used by the vision lane)."""
    with fitz.open(path) as doc:
        page = doc[index]
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("png")
