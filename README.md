<div align="center">

<img src="https://raw.githubusercontent.com/anishfyi/terbium/main/assets/logo.png" width="150" alt="terbium: a periodic-table tile reading 65 Tb terbium">

# terbium

**Catalogue in. Product catalog out.**
A god-level algorithmic parser for vendor catalogues: it reconstructs structure
from geometry, scores its own confidence, and only reaches for an AI model when
the algorithm cannot be sure.

[![License: MIT](https://img.shields.io/badge/license-MIT-000000.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-000000.svg)](pyproject.toml)
[![formats](https://img.shields.io/badge/PDF_PPTX_XLSX_CSV-000000.svg)](#what-it-parses)
[![version](https://img.shields.io/badge/version-0.9.6-000000.svg)](pyproject.toml)

[Website](https://anishfyi.github.io/terbium) · [Trove](https://github.com/anishfyi/trove)

</div>

---

<h3 align="center">Sponsors</h3>

<p align="center">
  <a href="https://go.nodemaven.com/terbiumGitHub" title="NodeMaven - residential and mobile proxies">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/anishfyi/terbium/main/assets/sponsors/nodemaven-dark.svg">
      <img src="https://raw.githubusercontent.com/anishfyi/terbium/main/assets/sponsors/nodemaven-light.svg" alt="NodeMaven" height="40">
    </picture>
  </a>
</p>

---

## The one thing terbium does

**Point it at any vendor catalogue and get back a table of products, each with its
name, its SKU, its materials or ingredients, and its image. Then a CSV.**

```python
import terbium

rows = terbium.build_catalog("vendor_catalogue.pdf", images_dir="images/")
terbium.to_catalog_csv(rows, "catalogue.csv")
# rows: {"sku": "RG-1001", "name": "Anatolia Kilim",
#        "materials": "wool", "image": "Anatolia_Kilim.jpeg", "page": 12}
```

Each product photo anchors a row: terbium extracts the image, names it from the
label beneath it, and mines the nearby text for the SKU and the materials. Clean
catalogues come out complete with no key; for a visual brochure that buries the
name in a title and the material in a paragraph, pass `ai=terbium.AI()` and a
vision model reads each photo plus the page text to fill the blanks. See
[docs/catalog.md](docs/catalog.md).

## Underneath: structure from geometry

A document carries most of its content as text but almost none of its structure.
A table in a PDF, a financial grid, a spec sheet, a schedule, a furniture
catalogue's size x finish matrix, is laid out for the eye; flatten it to text and
the columns collapse into a single line and the grid is gone. terbium rebuilds
that structure from the raw position of every word, on **any** column-aligned
table, and it is honest about how sure it is. The default detector is
content-agnostic; furniture is the worked example, not the limit.

Most parsers do one of two things: they fail silently on the hard pages, or they
throw the whole document at an LLM and bill you for the easy pages too. terbium
does neither. It solves what it can algorithmically, scores every record, and
when a page is genuinely ambiguous it either routes just that page to the right
model tier, or, if you gave it no key, tells you so in plain words.

## The loop

```
FILE  ->  ADAPT  ->  RECONSTRUCT  ->  SCORE  ->  [ESCALATE]
             |            |             |            |
       pdf/pptx/     columns, rows,  confidence   hard pages only:
       xlsx/csv      matrices from   per record   AI if key, else
                     geometry                      "add a key" message
```

| Phase | What happens |
|---|---|
| **Adapt** | One adapter per format normalizes bytes into positioned words + images |
| **Reconstruct** | Strip repeated headers, split two-page spreads, rebuild columns/rows/matrices from word geometry |
| **Score** | Every table gets a 0-1 confidence from grid regularity, header presence, and fill |
| **Escalate** | Below threshold: route the page to Haiku/Sonnet/Opus, or announce that a key would resolve it |

## Quickstart

```bash
pip install terbium-parse
```

```python
import terbium

rows = terbium.build_catalog("catalogue.pdf", images_dir="images/")   # no key needed
# each row: sku, name, materials, image, page

doc = terbium.parse("pricelist.xlsx", schema="product")   # raw records API
print(doc.stats)                                          # Stats(total=725, confident=712, ambiguous=13)

# opt into AI only for what the engine could not resolve
rows = terbium.build_catalog("lookbook.pdf", images_dir="images/",
                             ai=terbium.AI(anthropic_key="sk-..."))
```

Pull out the product images, each named after the product it sits under:

```python
manifest = terbium.export_images("lookbook.pdf", "out/")
# out/Kyoto_Bedside_Table.jpeg, out/Meadow_Bedside_Table.jpeg, ...
# manifest rows carry: product, collection, page, pixel size, colorspace,
# format, dpi, dominant_color, bbox
```

Run it from the shell:

```bash
terbium catalogue.pdf --csv out.csv         # the product table + images/, no AI
terbium lookbook.pdf --images out/          # extract product photos + manifest.csv
terbium report.xlsx --records --json out.json   # raw parsed records
```

## What it parses

| Format | Engine | How |
|---|---|---|
| **PDF** | word-level geometry | rebuild columns/rows/matrices from the position of every word |
| **PPTX** | python-pptx | native slides, tables and images, straight from the deck structure |
| **XLSX** | openpyxl | cells, merged ranges propagated, wide/long layouts |
| **CSV** | stdlib | delimiter, encoding and type inference |

PDF gets the full geometry engine because a PDF throws its structure away. PPTX,
XLSX and CSV already carry native structure, so terbium leans on it and parses
them cleanly and cheaply.

**Not every PDF is a matrix.** When a document is a lookbook, a grid of product
photos with a name under each, terbium reconstructs the label grid instead:
one record per product, grouped under its collection title. And when a page is
image-only, with no text layer at all, terbium does not return an empty result:
it reports exactly which pages need the vision lane.

## Confidence and escalation

terbium never pretends a shaky parse is solid. When it cannot be sure and no key
is set, it prints exactly what it could not do. On a records parse:

```
terbium: 712/725 records parsed confidently.
3 table(s) on page(s) 15, 26, 30 are ambiguous (no product title found above
the table; sparse matrix: 5/9 cells filled; 2 row(s) do not line up).
-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   recommended tier: Sonnet
```

And on a catalog build, when the data lives in the photos instead of the text:

```
terbium: 8/121 products have a name, 0 a SKU, 9 materials/ingredients.
82 page(s) are image-only (1, 5, 6, 7, 8, ...) - the data lives in the photos, not the text.
-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   recommended tier: Opus (vision)
```

Every record exposes its own `confidence` and the `reasons` behind it, so you can
filter, sort, or route on it yourself.

## The AI lane

The AI lane is opt-in and only ever sees the hard pages.

- **Routing.** Difficulty scales the tier: trivial to Haiku, moderate to Sonnet,
  hard or low-confidence to Opus. Pin a tier with `terbium.AI(force_tier="opus")`.
- **Arrange.** A hard table is handed to the routed model with the page's raw
  text and, for PDFs, a rendered image, and rebuilt into a clean matrix.
- **Vision.** Material icons (FSC, oiled, varnished) and finish swatches live only
  in the pixels; `terbium.read_images(path, page, ai)` reads them with a vision
  model. Note: Nano Banana (Gemini image) is for generation, not reading, so it is
  not on the parse path.

Keys come from `terbium.AI(...)` or the `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`
environment variables.

## Schemas

A schema turns reconstructed tables into typed records. Ships with three:

- `product`: universal, category-agnostic. Maps any table's columns to product
  fields by header meaning (sku/name/price/dimensions/color/material/qty/...);
  category-specific columns survive as attributes.
- `generic` (default for `parse`): one record per row for grids, one per cell
  for matrices.
- `furniture`: product, size, finish, and metric + imperial dimensions per SKU.

Add your own by subclassing `terbium.schema.Schema` and registering it.

## Install from source

```bash
git clone https://github.com/anishfyi/terbium.git
cd terbium
pip install -e .
```

## License

MIT. Built by [anishfyi](https://github.com/anishfyi).

<div align="center"><sub>terbium · Tb · 65</sub></div>
