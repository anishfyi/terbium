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


def _find_sku(lines: List[str]) -> Optional[str]:
    """A real product code: two+ letters with a digit, a separated code like
    ``MRP-962``, a 5-digit article, or a long barcode. Deliberately strict so page
    numbers, years, prices (``R350``), and dimensions (``28cm``) are not SKUs."""
    for text in lines:
        for tok in text.split():
            t = tok.strip(".,;:()[]")
            if not _SKU_TOK.match(t) or _DIM_TOK.match(t) or _ORD_TOK.match(t):
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


def _find_materials(lines: List[str], name: Optional[str]) -> Optional[str]:
    # an explicit "Material:/Ingredients:/Crafted from ..." line
    for ln in lines:
        low = ln.lower().strip()
        for label in _MAT_LABEL:
            if low.startswith(label):
                rest = ln[len(label):].lstrip(" :-–—").strip()
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


def _deterministic_rows(path: str, images_dir: str, **kw) -> List[dict]:
    manifest = export_images(path, images_dir, **kw)
    pages = {p.index: p for p in PdfAdapter().parse(path)}
    titles = {i: _page_title(p) for i, p in pages.items()}
    rows: List[dict] = []
    for m in manifest:
        page = pages.get(m["page"] - 1)
        caption = _caption_lines(page, m["bbox"]) if page else []
        page_lines = _page_lines(page) if page else []
        rows.append({
            "sku": _find_sku(caption) or _find_sku(page_lines),
            "name": m["product"] or titles.get(m["page"] - 1),
            "materials": _find_materials(caption + page_lines, m["product"]),
            "image": m["file"],
            "page": m["page"],
            "_context": " \n".join(caption + page_lines),
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
            "image": None,
            "page": r.source_page + 1,
        })
    return rows


def catalog_escalation(rows: List[dict]) -> Optional[str]:
    """The honest "bring an AI key" message for a half-blank catalog table.

    Fires when a meaningful share of rows is missing a name, SKU, or materials
    after the deterministic pass. Names the image-only pages (where the data
    lives in the photos, not the text) and recommends the vision tier for them.
    Returns None when the table is healthy enough to stay quiet.
    """
    total = len(rows)
    if not total:
        return None
    named = sum(1 for r in rows if r.get("name"))
    skus = sum(1 for r in rows if r.get("sku"))
    mats = sum(1 for r in rows if r.get("materials"))
    blank_share = 1 - min(named, max(skus, mats)) / total
    if named >= 0.6 * total and max(skus, mats) >= 0.6 * total:
        return None
    image_only = sorted({r["page"] for r in rows
                         if not (r.get("_context") or "").strip() and r.get("image")})
    page_str = ", ".join(str(p) for p in image_only[:8])
    if len(image_only) > 8:
        page_str += ", ..."
    lines = [
        f"terbium: {named}/{total} products have a name, {skus} a SKU, "
        f"{mats} materials/ingredients."
    ]
    if image_only:
        lines.append(
            f"{len(image_only)} page(s) are image-only ({page_str}) - "
            "the data lives in the photos, not the text."
        )
    tier = "Opus (vision)" if image_only and blank_share > 0.5 else "Sonnet"
    lines.append(
        "-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   "
        f"recommended tier: {tier}"
    )
    return "\n".join(lines)


def build_catalog(path: str, images_dir: Optional[str] = None, ai=None,
                  announce: bool = True, **kw) -> List[dict]:
    """Parse a catalogue into product rows: sku, name, materials, image, page.

    For image-bearing PDFs, each product photo anchors a row (name from the label
    beneath it; SKU and materials mined from nearby text). For pricelist-style
    catalogues (or when no photos are found), rows come from the product table.
    Pass ``ai`` to fill SKU/materials the layout hides (see ``enrich_catalog``).
    ``announce``: when the table comes back half-blank and no AI is in play,
    print the escalation message to stderr instead of staying silent.
    """
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    rows: List[dict] = []
    if ext == "pdf" and images_dir:
        rows = _deterministic_rows(path, images_dir, **kw)
    if not rows:
        rows = _table_rows(path, ai=ai)
    elif ai is not None and getattr(ai, "available", False):
        from .harness.catalog_ai import enrich_catalog

        rows = enrich_catalog(rows, path, images_dir, ai)
    if announce and (ai is None or not getattr(ai, "available", False)):
        msg = catalog_escalation(rows)
        if msg:
            print(msg, file=sys.stderr)
    for r in rows:
        r.pop("_context", None)
    return rows


CATALOG_COLUMNS = ["SKU", "Name", "Materials/Ingredients", "Image", "Page"]


def to_catalog_csv(rows: List[dict], path: Optional[str] = None) -> str:
    """Write the catalog table as a simple CSV: SKU, Name, Materials, Image."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CATALOG_COLUMNS)
    for r in rows:
        w.writerow([r.get("sku") or "", r.get("name") or "",
                    r.get("materials") or "", r.get("image") or "", r.get("page") or ""])
    out = buf.getvalue()
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
    return out
