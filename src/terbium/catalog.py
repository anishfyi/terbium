"""The catalog table: one row per product with name, SKU, materials, image.

This is terbium's headline job. Point it at any vendor catalogue and get back a
table of products, each with its name, its SKU (when the catalogue prints one),
its materials or ingredients, and the path to its extracted photo. A deterministic
pass handles the reliable parts (the photo and the name label under it) and mines
nearby text for a SKU and a materials line; an opt-in AI pass reads the product
image plus the page text to fill what prose layout hides (a material described in
a sentence, a code that only the picture makes sense of).
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
from typing import List, Optional

from .documents.pdf import PdfAdapter
from .extract import export_images
from .layout import signals
from .layout.lines import cluster_lines
from .normalize import MATERIAL_FAMILIES
from .schema.product import _looks_like_sku

# material vocabulary, longest first so "rubberwood" wins over "wood"
_MATERIAL_TERMS = sorted(
    {t for terms in MATERIAL_FAMILIES.values() for t in terms}, key=len, reverse=True
)
_MAT_LABEL = ("ingredients", "composition", "materials", "material", "made of",
              "made from", "crafted from", "fabric")


def _cx(w) -> float:
    return (w.x0 + w.x1) / 2


def _caption_lines(page, bbox) -> List[str]:
    """Lines sitting just below an image, horizontally aligned to it."""
    if not bbox:
        return []
    ix0, _, ix1, iy1 = bbox
    zone = [w for w in page.words if ix0 - 25 <= _cx(w) <= ix1 + 25 and iy1 - 6 <= w.y0 <= iy1 + 190]
    return [ln.text for ln in cluster_lines(zone) if ln.text.strip()]


def _page_lines(page) -> List[str]:
    return [ln.text for ln in cluster_lines(page.words) if ln.text.strip()]


_SKU_TOK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/\-]{2,19}$")
_DIM_TOK = re.compile(r"^\d+(?:\.\d+)?(?:cm|mm|m|ml|l|kg|g|in|\")$", re.IGNORECASE)
_ORD_TOK = re.compile(r"^\d+(?:st|nd|rd|th)$", re.IGNORECASE)          # 1st, 21st
_RATE_TOK = re.compile(r"^\d+(?:\.\d+)?/[A-Za-z]{1,6}\.?$")            # 2.25/SQFT, 40/PC


def _find_sku(lines: List[str]) -> Optional[str]:
    """A real product code: two+ letters with a digit, a separated code like
    ``MRP-962``, a 5-digit article, or a long barcode. Deliberately strict so page
    numbers, years, prices (``R350``), and dimensions (``28cm``) are not SKUs."""
    for text in lines:
        for tok in text.split():
            t = tok.strip(".,;:()[]")
            if not _SKU_TOK.match(t) or _DIM_TOK.match(t) or _ORD_TOK.match(t) \
                    or _RATE_TOK.match(t):
                continue
            alpha = sum(c.isalpha() for c in t)
            digits = sum(c.isdigit() for c in t)
            sep = any(c in "-_./" for c in t)
            if re.fullmatch(r"\d{5}", t) or digits >= 8:
                return t
            if digits >= 1 and (alpha >= 2 or (sep and alpha >= 1)):
                return t
    return None


_STOPWORDS = {"is", "are", "was", "a", "an", "the", "of", "and", "to", "with",
              "for", "from", "in", "on", "each", "we", "our", "that", "this", "by", "its"}


def _page_title(page) -> Optional[str]:
    """The largest, short heading on a page: a product or range name when no
    caption label sits under the photo. Prose is rejected via a stopword guard."""
    lines = [ln for ln in cluster_lines(page.words) if ln.text.strip()]
    if not lines:
        return None
    top = max(ln.max_size for ln in lines)
    for ln in sorted(lines, key=lambda l: -l.max_size):
        t = ln.text.strip()
        toks = t.split()
        if not (0 < len(toks) <= 5 and ln.max_size >= top * 0.9):
            continue
        if not t[0].isupper() or "," in t or t[-1] in ".,;:":
            continue                       # prose, not a heading
        if any(w.lower() in _STOPWORDS for w in toks):
            continue                       # a stopword means this is a sentence
        if t.lower().startswith(("space in-house", "these are", "www.", "page ")):
            continue
        return t
    return None


def _clean_name(t: Optional[str]) -> Optional[str]:
    """Reject OCR/heading junk ('TE', '--', 'S18') so a bad guess never beats a
    blank. Keeps only mostly-alphabetic strings of real length."""
    if not t:
        return None
    letters = sum(c.isalpha() for c in t)
    compact = t.replace(" ", "")
    if letters < 3 or (compact and letters < 0.6 * len(compact)):
        return None
    return t


def _find_materials(lines: List[str], name: Optional[str]) -> Optional[str]:
    # an explicit "Material:/Ingredients:/Crafted from ..." line
    for ln in lines:
        low = ln.lower().strip()
        for label in _MAT_LABEL:
            if low.startswith(label):
                rest = ln[len(label):].lstrip(" :-–-").strip()
                if rest:
                    return rest[:120]
    # a composition line: "78% polyacrylic, 20% polyester"
    for ln in lines:
        if signals.is_composition(ln):
            return ln.strip()[:120]
    # otherwise the material terms named anywhere on the page (skip the name line)
    blob = " \n".join(l for l in lines if l != name).lower()
    found = []
    for term in _MATERIAL_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", blob) and term not in found:
            found.append(term)
    if found:
        found.sort(key=lambda t: blob.find(t))
        return ", ".join(found[:3])
    return None


# "140X35X75 CM", "140 x 35 x 75", "45X35X60CM" - two or three axes, optional unit
_DIMENSIONS = re.compile(
    r"\b\d{1,4}(?:\.\d+)?\s*[xX×]\s*\d{1,4}(?:\.\d+)?"
    r"(?:\s*[xX×]\s*\d{1,4}(?:\.\d+)?)?\s*(?:cm|mm|m|in|inch|inches|\")?\b",
    re.IGNORECASE,
)


def _find_dimensions(lines: List[str]) -> Optional[str]:
    """The first L x W (x H) measurement printed near a product. The pattern
    requires an x/X/× between the numbers, so a lone figure never matches."""
    for ln in lines:
        m = _DIMENSIONS.search(ln)
        if m:
            return " ".join(m.group().split())[:60]
    return None


def _deterministic_rows(path: str, images_dir: str, ocr: bool = False, **kw) -> List[dict]:
    manifest = export_images(path, images_dir, **kw)
    pages = {p.index: p for p in PdfAdapter().parse(path)}
    if ocr:
        from .layout import ocr as _ocr
        _ocr.enrich_pdf_pages(list(pages.values()), path)   # fill text on image-only pages
    titles = {i: _page_title(p) for i, p in pages.items()}
    rows: List[dict] = []
    for m in manifest:
        page = pages.get(m["page"] - 1)
        caption = _caption_lines(page, m["bbox"]) if page else []
        page_lines = _page_lines(page) if page else []
        text = caption + page_lines
        rows.append({
            "sku": _find_sku(caption) or _find_sku(page_lines),
            # caption label, else the page's heading, else a plausible name
            # line from the caption zone (catalogues that print the product
            # name under the photo in body-size type, not as a heading)
            "name": (m["product"]
                     or _clean_name(titles.get(m["page"] - 1))
                     or _clean_name(_name_from_lines(caption))),
            "materials": _find_materials(text, m["product"]),
            "dimensions": _find_dimensions(text),
            "image": m["file"],
            "page": m["page"],
            "_context": " \n".join(text),
        })
    return rows


def _table_rows(path: str, ai=None) -> List[dict]:
    from .api import parse

    doc = parse(path, schema="product", ai=ai, announce=False)
    rows = []
    for r in doc.records:
        f = r.fields
        rows.append({
            "sku": r.sku,
            "name": f.get("name"),
            "materials": f.get("material") or f.get("materials") or f.get("ingredients"),
            "dimensions": f.get("dimensions") or f.get("size"),
            "image": None,
            "page": r.source_page + 1,
        })
    return rows


def _name_from_lines(lines: List[str]) -> Optional[str]:
    """A plausible product name from a slide/OCR text block: a short, alphabetic
    line that is not a dimension, SKU, or sentence."""
    for ln in lines:
        t = ln.strip()
        toks = t.split()
        if not (0 < len(toks) <= 6 and 2 <= len(t) <= 48):
            continue
        if _DIMENSIONS.search(t) or _find_sku([t]):
            continue
        if sum(c.isalpha() for c in t) < 2:
            continue
        if any(w.lower() in _STOPWORDS for w in toks):
            continue
        return t
    return None


def _pptx_rows(path: str, images_dir: str, ocr: bool = False, **kw) -> List[dict]:
    """Image-anchored rows for a PPTX deck: one row per product picture, named
    from slide text or (for pure-image slides) from OCR of the picture."""
    from .extract import export_pptx_images

    manifest = export_pptx_images(path, images_dir, ocr=ocr)
    rows: List[dict] = []
    for m in manifest:
        # Names come only from real slide text; picture-OCR is trusted for a
        # code/dimension but not for a free-text name (it hallucinates junk).
        slide_lines = [ln for ln in (m.get("slide_text") or "").split("\n") if ln.strip()]
        ocr_lines = [ln for ln in (m.get("ocr_text") or "").split("\n") if ln.strip()]
        all_lines = slide_lines + ocr_lines
        name = m.get("title") or _clean_name(_name_from_lines(slide_lines))
        rows.append({
            "sku": _find_sku(all_lines),
            "name": name,
            "materials": _find_materials(slide_lines, name),
            "dimensions": _find_dimensions(all_lines),
            "image": m["file"],
            "page": m["page"],
            "_context": " \n".join(slide_lines),
        })
    return rows


def catalog_escalation(rows: List[dict], ocr_ran: bool = False) -> Optional[str]:
    """The honest "there is more to read" message - and only when true.

    Escalates for two genuine reasons: pages with an image but no readable text
    even after OCR (the data is trapped in pixels, so vision could help), or a
    field that some rows carry but most lack (present-but-unread, which AI can
    fill). A field that is simply absent from the whole catalogue (e.g. a photo
    lookbook that prints no SKUs) is NOT a failure and stays silent.

    ``ocr_ran`` tunes the advice: if a local OCR pass already ran and text is
    still missing, the next lever is the vision lane, not "try OCR".
    """
    total = len(rows)
    if not total:
        return None
    image_only = sorted({r["page"] for r in rows
                         if not (r.get("_context") or "").strip() and r.get("image")})
    skus = sum(1 for r in rows if r.get("sku"))
    mats = sum(1 for r in rows if r.get("materials"))

    def partial(count: int) -> bool:            # some rows have it, most do not
        return 0.15 * total < count < 0.6 * total

    partial_sku, partial_mat = partial(skus), partial(mats)
    if not image_only and not partial_sku and not partial_mat:
        return None                             # everything the catalogue prints was read

    named = sum(1 for r in rows if r.get("name"))
    lines = [f"terbium: {total} products - {named} named, {skus} with a SKU, "
             f"{mats} with materials."]
    if image_only:
        pg = ", ".join(str(p) for p in image_only[:8])
        if len(image_only) > 8:
            pg += ", ..."
        lines.append(f"{len(image_only)} page(s) have no readable text ({pg}) - "
                     "the data is only in the photos.")
        if ocr_ran:
            lines.append("-> a local OCR pass already ran and still found no text there; "
                         "read them with the vision lane: ai=terbium.AI(...) with a key.")
        else:
            lines.append("-> run with ocr=True (local, no key) to read baked-in text, "
                         "or ai=terbium.AI(...) for the vision lane.")
    else:
        lines.append("-> some rows are missing a SKU/materials their neighbours have; "
                     "pass ai=terbium.AI(...) to fill the gaps.")
    return "\n".join(lines)


def build_catalog(path: str, images_dir: Optional[str] = None, ai=None,
                  announce: bool = True, ocr="auto", **kw) -> List[dict]:
    """Parse a catalogue into product rows: sku, name, materials, dimensions,
    image, page.

    For image-bearing PDFs and PPTX decks, each product photo anchors a row (name
    from the label beneath it; SKU, materials and dimensions mined from nearby
    text). For pricelist-style catalogues (or when no photos are found), rows come
    from the product table.

    ``ocr``: ``"auto"`` (default) runs a local Tesseract pass on image-only pages
    to read a code/name/dimensions the file baked into its pixels - no API key,
    no-op when Tesseract is absent. Pass ``True``/``False`` to force it.
    ``ai``: fills what even OCR cannot (materials hidden in prose, image-only
    reasoning). ``announce``: print the escalation message to stderr when the
    table is genuinely missing readable data.
    """
    from .layout import ocr as _ocr
    use_ocr = ocr if isinstance(ocr, bool) else (ocr == "auto" and _ocr.available())

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    rows: List[dict] = []
    if ext == "pdf" and images_dir:
        rows = _deterministic_rows(path, images_dir, ocr=use_ocr, **kw)
    elif ext == "pptx" and images_dir:
        rows = _pptx_rows(path, images_dir, ocr=use_ocr, **kw)
    if not rows:
        rows = _table_rows(path, ai=ai)
    elif ai is not None and getattr(ai, "available", False):
        from .harness.catalog_ai import enrich_catalog

        rows = enrich_catalog(rows, path, images_dir, ai)
    if announce and (ai is None or not getattr(ai, "available", False)):
        msg = catalog_escalation(rows, ocr_ran=use_ocr)
        if msg:
            print(msg, file=sys.stderr)
    for r in rows:
        r.pop("_context", None)
    return rows


CATALOG_COLUMNS = ["SKU", "Name", "Materials/Ingredients", "Dimensions", "Image", "Page"]


def to_catalog_csv(rows: List[dict], path: Optional[str] = None) -> str:
    """Write the catalog table as a simple CSV: SKU, Name, Materials, Dimensions,
    Image, Page."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CATALOG_COLUMNS)
    for r in rows:
        w.writerow([r.get("sku") or "", r.get("name") or "",
                    r.get("materials") or "", r.get("dimensions") or "",
                    r.get("image") or "", r.get("page") or ""])
    out = buf.getvalue()
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
    return out
