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


def test_csv_roundtrip(tmp_path):
    import terbium

    p = tmp_path / "p.csv"
    p.write_text("sku,product,price\n35155,Sequence table,1899\n50027,X table,1499\n")
    doc = terbium.parse(str(p), announce=False)
    assert doc.stats.total == 2
    assert {r.sku for r in doc.records} == {"35155", "50027"}
