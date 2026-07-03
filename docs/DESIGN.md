# terbium — a god-level algorithmic multi-file parser that knows when to call AI

**Status:** DRAFT design for approval (2026-07-03).
Repo target: github.com/anishfyi/terbium (public, MIT). Nothing created yet.
Landing: anishfyi.github.io/terbium. Trove-linked.

## Thesis
Vendor documents carry ~70% of their content as extractable text but ~0% of their
structure. terbium recovers the structure **algorithmically first** (geometry, not
guessing), scores its own confidence, and **only reaches for an AI model when it is
genuinely stuck** - and when no key is set, it tells you exactly that, in plain words.

Grounding example (Ethnicraft 2026 catalogue): 964 unique SKUs, 505 dimension rows,
0 prices, 1157 images (562 photo / 439 swatch / 156 material-icon). Each product page
is a 2-D matrix: rows = size, cols = finish, cells = article numbers.

## Core shape: algorithmic engine + confidence gate + opt-in AI
1. **`terbium` library** - pure Python, no AI, no network. The star of the show.
   file -> `ParsedDocument` (pages, layout-reconstructed blocks, typed signals,
   classified images, **per-record confidence**). Genuinely strong on its own.
2. **Confidence gate** - every record and page carries a 0-1 confidence + reasons.
   Below threshold => the page is "hard".
3. **`harness/` - opt-in AI layer.** If a key is present, hard pages route to a model
   tier by complexity and get the *arrange* + *vision* treatment. If NO key is
   present, terbium prints an actionable escalation message instead of failing:
   ```
   terbium: 47/52 products parsed confidently.
   5 pages have ambiguous matrices (orphan SKUs, uncertain column alignment).
   To resolve: set ANTHROPIC_API_KEY or pass ai=terbium.AI(...).
   Recommended tier for these pages: Opus.
   ```

## Formats (all first-class in v1)
| Format | Engine | Why algorithmic works |
|---|---|---|
| **PDF**  | PyMuPDF word-level bboxes | reconstruct columns/rows from token geometry |
| **PPTX** | python-pptx | slides -> shapes/tables/images with positions (tables native) |
| **XLSX** | openpyxl | cells, merged ranges, types, multi-sheet, wide/long detection |
| **CSV**  | stdlib + sniffer | delimiter/encoding/type inference, wide-matrix vs tidy |

## The algorithmic PDF engine (the "god-level" part)
Not pypdf flat text. Word-level bounding boxes, then:
1. **Repeated-element detection** - text recurring at the same (x,y) band across many
   pages => running header/footer => stripped.
2. **Column detection** - histogram of token left-edges; gaps => column boundaries.
3. **Row detection** - cluster tokens by baseline y => rows.
4. **Header inference** - finish-name row above a SKU block => column headers; leftmost
   dimension column => row headers.
5. **Matrix assembly** - each SKU cell assigned (row_header, col_header) by geometric
   alignment/containment.
6. **Signal typing** - regex for 5-digit SKU, `L×W×H cm | in`, composition `%`,
   markers `(new)`, `*`.
7. **Image classification** - by pixel area: icon(<64px) / swatch(mid) / photo(large).
8. **Confidence** - fraction of cells mapping to exactly one (row,col); orphan-cell
   count; column-count consistency; header certainty => 0-1 score + reasons.

## Repo layout
```
terbium/
  src/terbium/
    documents/        # multi-file adapters
      base.py         # DocumentAdapter -> Pages/Blocks/Images (+bboxes)
      pdf.py pptx.py xlsx.py csv.py
    layout/           # the algorithmic engine (format-agnostic)
      dehead.py       # repeated header/footer stripping
      grid.py         # column/row/matrix reconstruction from geometry
      signals.py      # SKU / dimension / dual-unit / composition detectors
      images.py       # icon | swatch | photo classification
      confidence.py   # scoring + reasons
    model/
      page.py record.py document.py
    schema/
      base.py furniture.py     # pluggable output shapes
    api.py            # parse(path, schema=?, ai=?) -> ParsedDocument
  harness/            # opt-in AI layer
    router.py         # complexity score -> haiku | sonnet | opus
    providers/ base.py anthropic.py gemini.py
    arrange.py        # rebuild hard matrices from blocks (+ rendered page image)
    vision.py         # read icons/swatches/attributes via a vision model
    prompts/
  docs/               # "the whole doc" + landing (index.html = anishfyi.github.io/terbium)
    quickstart.md formats.md schemas.md ai-and-routing.md confidence.md
    examples/furniture-catalogue.md
    index.html assets/           # brand landing page
  examples/furniture_catalogue.py
  tests/
  pyproject.toml  README.md  LICENSE(MIT)  assets/logo.svg
```

## API
```python
import terbium
doc = terbium.parse("Furniture Catalogue.pdf")                     # algorithmic only
print(doc.stats)   # {confident: 47, ambiguous: 5}; prints escalation if no key
doc = terbium.parse("catalogue.pdf", schema="furniture",
                     ai=terbium.AI(anthropic_key=..., gemini_key=...))  # AI on hard pages
for r in doc.records:
    print(r.sku, r.product, r.size, r.finish, r.dimensions_cm, r.confidence)
```

## Routing + vision
- score(page)=f(text_len, sku_count, column_count, image_count, has_matrix, confidence)
  -> trivial=Haiku, moderate=Sonnet, hard/low-confidence=Opus. Pinnable via env.
- **Vision** reads images (Ⓥ/FSC/Oiled icons, finish swatches) via Gemini/Claude vision.
  **Nano Banana** (Gemini 2.5 Flash Image) is generation/editing -> optional swatch
  normalization/thumbnails, NOT reading.

## Config / errors / testing
- Keys via env or `terbium.AI(...)`; none => algorithmic + escalation message.
- Typed adapter errors; AI retried; per-record confidence; bad pages => low-confidence
  partials, never a crash.
- Golden fixtures: pouf spread p60 (8 SKUs), a PPTX, an XLSX pricelist, a CSV. Unit
  tests for grid reconstruction, signals, image classification, confidence.

## Branding (Anish system - from querion/centauri/numera)
- Palette: bg #000 / #0b0b0d / #111114 / #17171b; line #1f1f25; fg #f0f0f2 / #9a9aa6 /
  #585862; accent #f4f4f6; per-lane accents for pdf/pptx/xlsx/csv + AI-escalation.
- Type: Bricolage Grotesque (display 800, -.04em), Hanken Grotesk (body), Space Mono
  (kickers/nav/badges, uppercase tracked).
- Motifs: sticky header + wordmark + accent dot + mono microtag; 48px grid w/ radial
  mask + soft glow; mono uppercase kickers w/ pulsing dot; primary/ghost buttons;
  readout chips.
- README: centered SVG wordmark (white TERBIUM on black rounded field, paths), bold
  tagline + subline, monochrome 000000 shields badges, Website - Trove nav line, ASCII
  loop diagram, phase table.
- LICENSE MIT, (c) 2026 anishfyi. Landing docs/index.html. Trove backlink everywhere.

## Confirmed by user
- Name terbium; formats PDF+PPTX+XLSX+CSV; algorithmic core with AI escalation; brand.
## To confirm on the final go
- PyPI package name availability (repo vs pip name can differ).
- Public repo creation on github.com/anishfyi (outward action - I will ask before creating).
