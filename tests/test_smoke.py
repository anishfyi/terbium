"""Smoke + golden tests that need no external files.

They cover the parts that are easy to get subtly wrong: signal regexes, 1-D
column clustering, grid reconstruction from synthetic geometry, confidence
scoring, and the CSV/XLSX round trip.
"""
from terbium.layout import signals
from terbium.layout.grid import _split_positions, extract_tables
from terbium.layout.confidence import score_table
from terbium.model.elements import Page, Word
from terbium.model.table import ExtractedTable


def test_signals_sku_and_dims():
    assert signals.find_skus("35155 and 200 x 100") == ["35155"]
    assert signals.find_skus("123456") == []  # 6 digits is not a 5-digit SKU
    dims = signals.find_dimensions("240 × 110 x 76 cm | 94.5\" x 43.5\"")
    assert dims and dims[0]["values"] == [240.0, 110.0, 76.0]
    assert signals.is_composition("78% polyacrylic, 20% polyester")
    assert signals.looks_like_axis_label("length x width x height")


def test_split_positions_finds_columns():
    # four tight clusters spread across a line
    centers = [100, 101, 200, 201, 300, 299, 400, 402]
    ranges = _split_positions(centers, 4)
    assert len(ranges) == 4


def _word(text, x, y, size=10.0, bold=False):
    return Word(text=text, x0=x, y0=y, x1=x + 8 * len(text), y1=y + 10, size=size, bold=bold)


def test_grid_reconstructs_a_matrix():
    # a synthetic 1-product page: title, axis+finish header, two size rows
    words = []
    words.append(_word("Barrow pouf", 50, 10, size=16, bold=True))
    # header line: axis label on the left, two finishes on the right
    words += [_word("length", 50, 40), _word("x", 90, 40), _word("width", 100, 40)]
    words += [_word("off white", 300, 40), _word("ginger", 450, 40)]
    # data row 1
    words += [_word("40 × 40 cm", 50, 70), _word("20156", 300, 70), _word("20154", 450, 70)]
    # data row 2
    words += [_word("60 × 60 cm", 50, 100), _word("20157", 300, 100), _word("20155", 450, 100)]
    page = Page(index=0, width=600, height=800, words=words, source_kind="pdf")

    from terbium.layout.lines import cluster_lines

    tables = extract_tables(cluster_lines(words), page)
    assert len(tables) == 1
    t = tables[0]
    assert t.title == "Barrow pouf"
    assert t.n_rows == 2 and t.n_cols == 2
    # every cell filled, mapped to the right column
    assert t.cells[0] == ["20156", "20154"]
    assert t.cells[1] == ["20157", "20155"]
    conf, reasons = score_table(t)
    assert conf > 0.9


def test_sparse_matrix_scores_lower():
    t = ExtractedTable(
        title=None,
        row_headers=["a", "b"],
        col_headers=["c1", "c2", "c3"],
        cells=[["1", None, None], ["2", None, None]],
        source_page=0,
        kind="matrix",
    )
    conf, reasons = score_table(t)
    assert conf < 0.72
    assert any("sparse" in r for r in reasons)


def test_generic_table_detector_is_content_agnostic():
    # a plain financial table: no dimensions, no SKUs. The default detector must
    # still reconstruct it purely from column geometry.
    from terbium.layout.tables import detect_tables
    from terbium.layout.lines import cluster_lines

    def w(t, x, y):
        return Word(text=t, x0=x, y0=y, x1=x + 8 * len(t), y1=y + 10, size=11)

    words = [
        w("Region", 60, 50), w("Q1", 240, 50), w("Growth", 380, 50),
        w("North", 60, 90), w("1204", 240, 90), w("28%", 380, 90),
        w("South", 60, 122), w("980", 240, 122), w("14%", 380, 122),
    ]
    page = Page(index=0, width=520, height=700, words=words, source_kind="pdf")
    tables = detect_tables(cluster_lines(words), page)
    assert len(tables) == 1
    t = tables[0]
    assert t.col_headers == ["Region", "Q1", "Growth"]
    assert t.cells[0] == ["North", "1204", "28%"]
    assert t.cells[1] == ["South", "980", "14%"]


def test_prose_columns_are_not_a_table():
    # two-column prose must not be mistaken for a data table
    from terbium.layout.tables import detect_tables
    from terbium.layout.lines import cluster_lines

    def w(t, x, y):
        return Word(text=t, x0=x, y0=y, x1=x + 7 * len(t), y1=y + 10, size=11)

    left = "For thirty years we have made furniture shaped by material and purpose".split()
    right = "Each piece is developed to be lived with and to age gracefully over time".split()
    words = []
    for i, tok in enumerate(left):
        words.append(w(tok, 40 + (i % 6) * 30, 60 + (i // 6) * 20))
    for i, tok in enumerate(right):
        words.append(w(tok, 300 + (i % 6) * 30, 60 + (i // 6) * 20))
    page = Page(index=0, width=520, height=700, words=words, source_kind="pdf")
    assert detect_tables(cluster_lines(words), page) == []


def test_label_grid_extraction():
    # a synthetic lookbook page: a collection title + a 2-column grid of names,
    # one of which wraps onto a second line.
    from terbium.layout.labels import extract_labels
    from terbium.layout.lines import cluster_lines
    from terbium.model.elements import ImageRef

    def w(text, x0, y, size=12.0):
        return Word(text=text, x0=x0, y0=y, x1=x0 + 8 * len(text), y1=y + 10, size=size)

    words = [
        w("Bedside", 60, 10, size=16), w("Collection", 112, 10, size=16),   # title
        w("Kyoto", 140, 200), w("Bedside", 182, 200),                       # col A row 1
        w("Meadow", 380, 200), w("Bedside", 432, 200),                      # col B row 1
        w("Table", 400, 228),                                               # col B row 1 wrap
        w("Raas", 140, 400), w("Bedside", 177, 400), w("Table", 227, 400),  # col A row 2
        w("Coco", 380, 400), w("Bedside", 417, 400),                        # col B row 2
    ]
    page = Page(index=0, width=600, height=800, words=words, source_kind="pdf",
                images=[ImageRef(page=0, width=200, height=200) for _ in range(4)])
    t = extract_labels(cluster_lines(words), page)
    assert t is not None and t.title == "Bedside Collection"
    names = {c[0] for c in t.cells}
    assert "Meadow Bedside Table" in names   # wrapped label stitched back together
    assert "Kyoto Bedside" in names
    assert "Raas Bedside Table" in names


def test_labels_need_a_grid_not_prose():
    # a single image + one line is prose, not a label grid -> no extraction
    from terbium.layout.labels import extract_labels
    from terbium.layout.lines import cluster_lines
    from terbium.model.elements import ImageRef

    words = [Word(text="Virasat", x0=100, y0=100, x1=160, y1=112, size=14)]
    page = Page(index=0, width=600, height=800, words=words, source_kind="pdf",
                images=[ImageRef(page=0, width=400, height=400)])
    assert extract_labels(cluster_lines(words), page) is None


def test_image_label_association():
    # a photo should bind to the label sitting just below it, not a distant one
    from terbium.extract import _associate

    items = [
        {"name": "Kyoto Bedside Table", "cx": 200, "y": 280, "size": 12},
        {"name": "Far Away", "cx": 900, "y": 280, "size": 12},
        {"name": "Above It", "cx": 200, "y": 20, "size": 12},
    ]
    assert _associate((100, 50, 300, 250), items) == "Kyoto Bedside Table"
    assert _associate((100, 50, 300, 250), []) is None


def test_product_schema_is_category_agnostic():
    # a bag pricelist with headers unlike any furniture catalogue
    from terbium.schema.product import ProductSchema

    t = ExtractedTable(
        title=None,
        row_headers=["", ""],
        col_headers=["Style Code", "Name", "Material", "Capacity", "Colour", "MRP"],
        cells=[
            ["BG-22", "Weekender", "Leather", "35L", "Tan", "₹12999"],
            ["BG-23", "City Tote", "Canvas", "14L", "Olive", "₹4499"],
        ],
        source_page=0,
        kind="grid",
    )
    r = ProductSchema().build_records([t])[0]
    assert r.sku == "BG-22"
    assert r.fields["name"] == "Weekender"
    assert r.fields["material"] == "Leather"
    assert r.fields["color"] == "Tan"
    assert r.fields["price_amount"] == 12999.0 and r.fields["currency"] == "INR"
    assert r.fields["Capacity"] == "35L"     # category-specific attribute preserved


def test_product_header_longest_match():
    # "Pack Size" must map to quantity, not dimensions (which also contains "size")
    from terbium.schema.product import _map_header

    assert _map_header("Pack Size") == "quantity"
    assert _map_header("Size") == "dimensions"
    assert _map_header("Article Number") == "sku"


def test_normalization_families_and_dimensions():
    from terbium.normalize import color_family, material_family, dimensions_mm

    assert color_family("Off White") == "white"     # longest term wins over "white"
    assert color_family("Terracotta") == "red"
    assert material_family("Full-grain Leather") == "leather"
    assert material_family("Polypropylene") == "textile"
    assert dimensions_mm("160 x 230 cm")["values_mm"] == [1600.0, 2300.0]
    assert dimensions_mm("no dimensions here") is None


def test_catalog_end_to_end_all_four_fields(tmp_path):
    # generate a tiny lookbook PDF (real embedded photos + captions) and confirm
    # build_catalog recovers name, SKU, materials, and the image file for a product
    import io

    import fitz
    from PIL import Image

    import terbium

    def photo(c):
        buf = io.BytesIO()
        Image.new("RGB", (400, 300), c).save(buf, format="PNG")
        return buf.getvalue()

    doc = fitz.open()
    pg = doc.new_page(width=820, height=1040)
    products = [("Anatolia Kilim", "RUG-101", "Material: Wool", (170, 90, 70)),
                ("Citrus Hand Wash", "HW-602", "Ingredients: Aqua, Grapefruit", (90, 130, 110))]
    for i, (name, sku, mat, col) in enumerate(products):
        y0 = 40 + i * 480
        pg.insert_image(fitz.Rect(40, y0, 340, y0 + 220), stream=photo(col))
        pg.insert_text((40, y0 + 244), name, fontsize=15)
        pg.insert_text((40, y0 + 312), f"SKU: {sku}", fontsize=10)
        pg.insert_text((40, y0 + 330), mat, fontsize=10)
    path = str(tmp_path / "lookbook.pdf")
    doc.save(path)
    doc.close()

    rows = terbium.build_catalog(path, images_dir=str(tmp_path / "img"), only_photos=False)
    by_name = {r["name"].strip().lower(): r for r in rows if r.get("name")}
    rug = by_name["anatolia kilim"]
    assert rug["sku"] == "RUG-101"
    assert "wool" in (rug["materials"] or "").lower()
    assert rug["image"] and (tmp_path / "img" / rug["image"]).exists()
    wash = by_name["citrus hand wash"]
    assert wash["sku"] == "HW-602"
    assert "aqua" in (wash["materials"] or "").lower()      # ingredients, not materials


def test_catalog_helpers_and_sku_strictness():
    from terbium.catalog import _find_sku, _find_materials, to_catalog_csv

    # strict SKU: real codes yes, page numbers / prices no
    assert _find_sku(["RG-1001 Anatolia Kilim"]) == "RG-1001"
    assert _find_sku(["20156"]) == "20156"           # 5-digit article
    assert _find_sku(["Page 12", "1899", "2026"]) is None
    # materials from a labelled line and from prose material terms
    assert _find_materials(["Material: Solid Oak"], None) == "Solid Oak"
    assert _find_materials(["Crafted from solid mango wood"], None).startswith("solid mango wood") \
        or _find_materials(["Crafted from solid mango wood"], None) == "mango, wood"
    csv_text = to_catalog_csv([{"sku": "RG-1", "name": "Kilim", "materials": "wool",
                                "image": "kilim.jpg", "page": 2}])
    assert csv_text.splitlines()[0] == "SKU,Name,Materials/Ingredients,Image,Page"
    assert "RG-1,Kilim,wool,kilim.jpg,2" in csv_text


def test_catalog_ai_fills_blanks(monkeypatch):
    # the AI pass fills name/sku/materials the deterministic pass left blank
    from terbium.harness import catalog_ai

    class Stub:
        def complete(self, prompt, system, tier, image_png=None):
            return '{"name":"Virasat Sideboard","sku":null,"materials":"solid mango wood"}'

    monkeypatch.setattr(catalog_ai, "vision_provider", lambda ai: Stub())

    class FakeAI:
        available = True
        force_tier = None

    rows = [{"name": None, "sku": None, "materials": None, "image": None,
             "page": 4, "_context": "Virasat, solid mango wood"}]
    out = catalog_ai.enrich_catalog(rows, "x.pdf", None, FakeAI())
    assert out[0]["name"] == "Virasat Sideboard"
    assert out[0]["materials"] == "solid mango wood"
    assert out[0]["sku"] is None                      # model told not to invent one


def test_ai_enrich_plumbing(monkeypatch):
    # verify the AI enrichment layer end-to-end with a stubbed provider (no key)
    from terbium.harness import product_ai
    from terbium.harness.ai import AI
    from terbium.model.record import Record

    class Stub:
        def complete(self, prompt, system, tier, image_png=None):
            return (
                '{"name":"Anatolia Kilim","sku":"RG-1001","category":"rug",'
                '"price":{"amount":249,"currency":"GBP"},"color":"terracotta",'
                '"material":"wool","attributes":{"weave":"flatweave","pattern":"geometric"},'
                '"confidence":0.95}'
            )

    monkeypatch.setattr(product_ai, "text_provider", lambda ai: Stub())
    ai = AI(anthropic_key="test-key")
    recs = [Record(sku="RG-1001", fields={"name": "Anatolia Kilim"}, source_page=0, confidence=0.5)]
    r = product_ai.enrich_records(recs, ai)[0]
    assert r.origin == "ai"
    assert r.fields["category"] == "rug"
    assert r.fields["material"] == "wool"
    assert r.fields["weave"] == "flatweave"          # implicit attribute folded in
    assert r.fields["price_amount"] == 249 and r.fields["currency"] == "GBP"
    assert r.confidence == 0.95


def test_feed_exporters():
    import json
    from terbium.export_feed import to_shopify_csv, to_pim_json
    from terbium.model.record import Record

    recs = [Record(
        sku="RG-1001",
        fields={"name": "Anatolia Kilim", "color": "Terracotta", "color_family": "red",
                "material": "Wool", "material_family": "textile", "price_amount": 249.0,
                "category": "rug"},
        source_page=0, confidence=0.9,
    )]
    csv_text = to_shopify_csv(recs)
    assert csv_text.startswith("Handle,Title")
    assert "anatolia-kilim" in csv_text and "RG-1001" in csv_text and "249.0" in csv_text
    assert "red, textile" in csv_text            # families become tags
    pim = json.loads(to_pim_json(recs))
    assert pim[0]["sku"] == "RG-1001" and pim[0]["color_family"] == "red"


def test_csv_roundtrip(tmp_path):
    import terbium

    p = tmp_path / "p.csv"
    p.write_text("sku,product,price\n35155,Sequence table,1899\n50027,X table,1499\n")
    doc = terbium.parse(str(p), announce=False)
    assert doc.stats.total == 2
    assert {r.sku for r in doc.records} == {"35155", "50027"}


def test_catalog_escalation_fires_on_blank_table():
    from terbium.catalog import catalog_escalation

    rows = [{"sku": None, "name": None, "materials": None, "image": f"p{i}.jpeg",
             "page": i, "_context": ""} for i in range(1, 11)]
    rows[0].update(name="Virasat", _context="Virasat solid mango wood")
    msg = catalog_escalation(rows)
    assert msg is not None
    assert "1/10 products have a name" in msg
    assert "image-only" in msg and "Opus (vision)" in msg
    assert "ai=terbium.AI(...)" in msg


def test_catalog_escalation_quiet_when_healthy():
    from terbium.catalog import catalog_escalation

    rows = [{"sku": f"RG-{i}", "name": f"Rug {i}", "materials": "wool",
             "image": None, "page": 1, "_context": "text"} for i in range(10)]
    assert catalog_escalation(rows) is None
    assert catalog_escalation([]) is None
