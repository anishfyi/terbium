<div align="center">

<img src="https://raw.githubusercontent.com/anishfyi/terbium/main/assets/logo.png" width="150" alt="terbium: a periodic-table tile reading 65 Tb terbium">

# terbium

**A god-level algorithmic multi-file parser that knows when it is stuck.**
It reconstructs a document's structure from geometry, scores its own confidence,
and only reaches for an AI model when the algorithm cannot be sure.

[![License: MIT](https://img.shields.io/badge/license-MIT-000000.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-000000.svg)](pyproject.toml)
[![formats](https://img.shields.io/badge/PDF_PPTX_XLSX_CSV-000000.svg)](#what-it-parses)
[![version](https://img.shields.io/badge/version-0.1.0-000000.svg)](pyproject.toml)

[Website](https://anishfyi.github.io/terbium) · [Trove](https://github.com/anishfyi/trove)

</div>

---

A vendor document carries most of its content as text but almost none of its
structure. A furniture catalogue page is a 2-D matrix: rows are sizes, columns
are finishes, and the cells are article numbers. Flatten it to text and the grid
is gone, the columns collapse into a single line, and the numbers lose their
meaning. terbium rebuilds that structure from the raw position of every word,
and it is honest about how sure it is.

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

doc = terbium.parse("Furniture Catalogue.pdf")     # algorithmic only, no key needed
print(doc.stats)                                    # Stats(total=725, confident=712, ambiguous=13)

for r in doc.records:
    print(r.sku, r.fields)

# opt into AI only for the pages the engine could not resolve
doc = terbium.parse("Furniture Catalogue.pdf",
                    schema="furniture",
                    ai=terbium.AI(anthropic_key="sk-..."))
```

Run it from the shell:

```bash
terbium "Furniture Catalogue.pdf" --schema furniture
terbium report.xlsx --json out.json
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

## Confidence and escalation

terbium never pretends a shaky parse is solid. When it cannot be sure and no key
is set, it prints exactly what it could not do:

```
terbium: 712/725 records parsed confidently.
3 table(s) on page(s) 15, 26, 30 are ambiguous (no product title found above
the table; sparse matrix: 5/9 cells filled; 2 row(s) do not line up).
-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   recommended tier: Sonnet
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

A schema turns reconstructed tables into typed records. Ships with two:

- `generic` (default): one record per row for grids, one per cell for matrices.
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
