"""Local OCR lane - read text that a catalogue baked into its page images.

Many vendor catalogues are flattened exports (InDesign/Canva/PowerPoint) with no
text layer: the product code, name, and dimensions live in the pixels. terbium's
algorithmic lanes need words, so this synthesizes a word layer with Tesseract
(via PyMuPDF's built-in bridge - no extra Python dependency) and hands it back in
exactly the shape the PDF adapter produces, so every downstream lane just works.

It is strictly opt-in and degrades to a no-op when Tesseract is not installed, so
terbium never hard-depends on it.
"""
from __future__ import annotations

import contextlib
import os
import shutil
from typing import List, Optional

import fitz

from ..model.elements import Word
from ..documents.pdf import _span_words


@contextlib.contextmanager
def _quiet():
    """Silence Tesseract/MuPDF C-level chatter ('Image too small to scale',
    'Line cannot be recognized') that would otherwise spam stderr per page."""
    try:
        fitz.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass
    try:
        saved = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
    except Exception:
        saved = None
        devnull = None
    try:
        yield
    finally:
        if saved is not None:
            try:
                os.dup2(saved, 2)
                os.close(saved)
            except Exception:
                pass
        if devnull is not None:
            try:
                os.close(devnull)
            except Exception:
                pass

_TESSDATA_CANDIDATES = (
    "/opt/homebrew/share/tessdata",
    "/usr/local/share/tessdata",
    "/usr/share/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tesseract-ocr/5/tessdata",
    "/opt/local/share/tessdata",
)

_AVAILABLE: Optional[bool] = None


def _ensure_tessdata() -> None:
    """PyMuPDF's OCR needs TESSDATA_PREFIX. Point it at a real tessdata dir if
    the environment has not already."""
    if os.environ.get("TESSDATA_PREFIX") and os.path.isdir(os.environ["TESSDATA_PREFIX"]):
        return
    for cand in _TESSDATA_CANDIDATES:
        if os.path.isdir(cand):
            os.environ["TESSDATA_PREFIX"] = cand
            return


def available() -> bool:
    """True when a local Tesseract is usable. Probed once and cached."""
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE
    _AVAILABLE = False
    if shutil.which("tesseract") is None:
        return False
    _ensure_tessdata()
    try:
        with _quiet():
            doc = fitz.open()
            page = doc.new_page(width=120, height=60)
            page.insert_text((10, 30), "ocr")
            tp = page.get_textpage_ocr(dpi=72, full=True)
            page.get_text("dict", textpage=tp)
            doc.close()
        _AVAILABLE = True
    except Exception:
        _AVAILABLE = False
    return _AVAILABLE


def _words_from_textpage(page, textpage) -> List[Word]:
    words: List[Word] = []
    data = page.get_text("dict", textpage=textpage)
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                words.extend(_span_words(span))
    return words


def ocr_page_words(page, dpi: int = 300) -> List[Word]:
    """OCR a fitz page and return positioned words in page-point coordinates."""
    try:
        with _quiet():
            tp = page.get_textpage_ocr(dpi=dpi, full=True)
            return _words_from_textpage(page, tp)
    except Exception:
        return []


def ocr_image_words(blob: bytes, dpi: int = 300) -> List[Word]:
    """OCR raw image bytes (a PPTX picture), returning positioned words."""
    try:
        doc = fitz.open(stream=blob, filetype=_sniff(blob))
    except Exception:
        return []
    try:
        if doc.page_count == 0:
            return []
        return ocr_page_words(doc[0], dpi=dpi)
    finally:
        doc.close()


def _sniff(blob: bytes) -> str:
    if blob[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return "png"


def enrich_pdf_pages(pages, path: str, min_words: int = 3, dpi: int = 300) -> int:
    """For each image-bearing page with almost no text layer, OCR it and fill
    ``page.words``. Returns the number of pages enriched (0 if OCR unavailable)."""
    if not available():
        return 0
    targets = [p for p in pages
               if getattr(p, "source_kind", "pdf") == "pdf"
               and p.images and len(p.words) < min_words]
    if not targets:
        return 0
    enriched = 0
    with fitz.open(path) as doc:
        for p in targets:
            if p.index >= doc.page_count:
                continue
            w = ocr_page_words(doc[p.index], dpi=dpi)
            if w:
                p.words = w
                enriched += 1
    return enriched
