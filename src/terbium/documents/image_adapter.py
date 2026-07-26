"""Image file adapter: PNG/JPG/JPEG/WEBP/TIFF -> single Page with OCR words."""
from __future__ import annotations

import os
from typing import List

from ..layout.images import classify
from ..layout import ocr as _ocr
from ..model.elements import ImageRef, Page, Word
from .base import DocumentAdapter, register


@register
class ImageAdapter(DocumentAdapter):
    extensions = ("png", "jpg", "jpeg", "webp", "tiff", "tif")

    def parse(self, path: str) -> List[Page]:
        with open(path, "rb") as fh:
            blob = fh.read()
        words: List[Word] = []
        if _ocr.available():
            words = _ocr.ocr_image_words(blob)
        try:
            from PIL import Image

            with Image.open(path) as im:
                w, h = im.size
        except Exception:
            w, h = 800, 600
        kind = classify(w, h)
        page = Page(
            index=0,
            width=float(w),
            height=float(h),
            words=words,
            images=[ImageRef(page=0, width=w, height=h, kind=kind, bbox=(0, 0, float(w), float(h)))],
            source_kind="image",
        )
        return [page]
