"""Cross-category proof: generate a representative lookbook PDF for each of the
six named product categories (real embedded photos + name/SKU/materials captions),
run terbium.build_catalog on it, and score name/SKU/materials/image recall.

The PDFs are synthetic but structurally faithful to a real vendor lookbook: a grid
of product photos, each with its name directly beneath, and the SKU and materials
lines below that. No AI key is used; this measures the deterministic engine.

    python eval/category_bench.py
"""
from __future__ import annotations

import io
import os
import tempfile

import fitz
from PIL import Image, ImageDraw

import terbium

# category -> list of (name, sku, materials/ingredients line)
CATEGORIES = {
    "rugs": [
        ("Anatolia Kilim", "RUG-101", "Material: Wool"),
        ("Nordic Shag", "RUG-102", "Material: Polypropylene"),
        ("Persian Medallion", "RUG-103", "Material: Silk"),
        ("Jute Weave", "RUG-104", "Material: Jute"),
    ],
    "lamps": [
        ("Arc Floor Lamp", "LMP-201", "Material: Brushed Brass"),
        ("Dome Table Lamp", "LMP-202", "Material: Steel"),
        ("Paper Pendant", "LMP-203", "Material: Rice Paper"),
        ("Marble Task Lamp", "LMP-204", "Material: Marble"),
    ],
    "bags": [
        ("Weekender Holdall", "BAG-301", "Material: Leather"),
        ("City Tote", "BAG-302", "Material: Canvas"),
        ("Sling Pack", "BAG-303", "Material: Nylon"),
        ("Duffel Pro", "BAG-304", "Material: Polyester"),
    ],
    "handbags": [
        ("Quilted Clutch", "HBG-401", "Material: Lambskin"),
        ("Chain Shoulder", "HBG-402", "Material: Leather"),
        ("Bucket Bag", "HBG-403", "Material: Suede"),
        ("Top Handle", "HBG-404", "Material: Saffiano"),
    ],
    "cushions": [
        ("Velvet Lumbar", "CSH-501", "Material: Velvet"),
        ("Linen Square", "CSH-502", "Material: Linen"),
        ("Boucle Round", "CSH-503", "Material: Cotton"),
        ("Silk Bolster", "CSH-504", "Material: Silk"),
    ],
    "handwash": [
        ("Botanical Hand Wash", "HW-601", "Ingredients: Aqua, Glycerin, Lavender Oil"),
        ("Citrus Hand Wash", "HW-602", "Ingredients: Aqua, Grapefruit Extract"),
        ("Oat Milk Hand Wash", "HW-603", "Ingredients: Aqua, Oat Extract, Shea"),
        ("Charcoal Hand Wash", "HW-604", "Ingredients: Aqua, Charcoal, Tea Tree"),
    ],
}

_PALETTE = [(176, 96, 72), (120, 140, 108), (90, 110, 150), (150, 120, 60),
            (110, 90, 130), (80, 120, 120)]


def _photo(seed: int) -> bytes:
    c = _PALETTE[seed % len(_PALETTE)]
    im = Image.new("RGB", (420, 320), c)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, 380, 280], outline=(255, 255, 255), width=6)
    d.ellipse([120, 90, 300, 230], fill=tuple(min(255, v + 40) for v in c))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def make_pdf(products, path):
    doc = fitz.open()
    page = doc.new_page(width=820, height=1040)
    for i, (name, sku, material) in enumerate(products):
        col, row = i % 2, i // 2
        x0 = 40 + col * 400
        y0 = 40 + row * 480
        page.insert_image(fitz.Rect(x0, y0, x0 + 300, y0 + 220), stream=_photo(i))
        page.insert_text((x0, y0 + 244), name, fontsize=15)          # name under photo
        page.insert_text((x0, y0 + 312), f"SKU: {sku}", fontsize=10)  # spaced below
        page.insert_text((x0, y0 + 330), material, fontsize=10)
    doc.save(path)
    doc.close()


def score(products, rows):
    got = {}
    for r in rows:
        if r.get("name"):
            got[r["name"].strip().lower()] = r
    n = len(products)
    name_hit = sku_hit = mat_hit = img_hit = 0
    for name, sku, material in products:
        r = got.get(name.lower())
        if not r:
            continue
        name_hit += 1
        if r.get("image"):
            img_hit += 1
        if r.get("sku") == sku:
            sku_hit += 1
        expected = material.split(":", 1)[1].split(",")[0].strip().lower()
        if r.get("materials") and expected in r["materials"].lower():
            mat_hit += 1
    return name_hit, sku_hit, mat_hit, img_hit, n


def main():
    tmp = tempfile.mkdtemp(prefix="terbium_cat_bench_")
    print(f"{'category':<10} {'products':>8} {'name':>6} {'sku':>6} {'material':>9} {'image':>6}")
    print("-" * 52)
    totals = [0, 0, 0, 0, 0]
    for cat, products in CATEGORIES.items():
        pdf = os.path.join(tmp, f"{cat}.pdf")
        make_pdf(products, pdf)
        rows = terbium.build_catalog(pdf, images_dir=os.path.join(tmp, f"{cat}_img"),
                                     only_photos=False)
        nh, sh, mh, ih, n = score(products, rows)
        print(f"{cat:<10} {n:>8} {nh:>6} {sh:>6} {mh:>9} {ih:>6}")
        for j, v in enumerate((nh, sh, mh, ih, n)):
            totals[j] += v
    print("-" * 52)
    nh, sh, mh, ih, n = totals
    print(f"{'TOTAL':<10} {n:>8} {nh:>6} {sh:>6} {mh:>9} {ih:>6}")
    print(f"\nname {nh}/{n}  sku {sh}/{n}  materials {mh}/{n}  image {ih}/{n}")


if __name__ == "__main__":
    main()
