# terbium roadmap: the best catalogue-to-commerce parser

**Goal.** Be the best parser on the internet for turning any vendor catalogue,
across any product category (furniture, rugs, lamps, bags, cushions, handwash,
anything), into clean, normalized product records plus the linked product images.

## The positioning, grounded in today's landscape

The 2026 benchmarks (OmniDocBench, Applied AI's PDFbench over 800+ docs) show one
thing clearly: **document type determines accuracy more than parser choice**, with
55+ point swings between domains. General PDF-to-markdown is already owned, Gemini
3 Pro (~88% edit similarity) and GPT-5.1 (~84%) lead, and Reducto, LlamaParse, and
Docling compete hard on RAG output. Trying to be "the best general parser" is a
losing fight.

So we do not compete there. Those tools output **markdown/text for RAG**. terbium
outputs **structured product records for commerce**: name, SKU, price, category,
category-appropriate attributes, and the product photo, ready for a PIM, Shopify,
or a marketplace feed. Nobody owns "catalogue in, clean product catalog out." That
is the niche we win, and it is where vendor documents (the messy, image-heavy,
cross-tab PDFs we already handle) actually live.

## Phased plan

| Phase | Deliverable | State |
|---|---|---|
| 0 | Generic engine: tables, labels, images, confidence, escalation | done (0.4.0) |
| 1 | Universal `product` schema (category-agnostic column mapping) | done (0.5.0) |
| 2 | AI enrich layer: implicit attributes + vision reads | done (0.6.0) |
| 3 | Normalization: units, currency, color/material taxonomies | done (0.7.0) |
| 4 | Evaluation harness + public benchmark vs the field | done (0.8.0) |
| 5 | Feed exporters (Shopify CSV, Google Merchant, generic PIM JSON) | done (0.9.0) |
| 6 | Multi-document expansion: classify, transactions, resumes, universal output | done (0.10.0) |
| 7 | Dense/sparse catalog improvements + image adapter | done (0.10.0) |
| 8 | Public benchmark publication + category golden sets | next |

## 0.10.0 (shipped)

- **Classification** (`classify.py`): auto-routes catalog, transaction, resume,
  table, deck, and lookbook inputs after adapter parse.
- **Transaction + resume schemas** with FIELD_SYNONYMS and form/key-value extraction.
- **Universal output**: CSV, HTML, and terminal tables with never-crash fallback chains.
- **Image adapter**: PNG/JPG/JPEG/WEBP/TIFF via Tesseract OCR bridge.
- **Picture-heavy catalogs**: per-page lookbook heuristic, proximity caption scoring,
  dense grid (12/page) and sparse (1/page) support, swatch retry in main pass.
- **Transaction AI lane**: Anthropic-first fill modeled on `catalog_ai`.

See [documents.md](documents.md) for CLI and API details.

## Risks and honest limits

- Some catalogues (like the Fable Room teaser deck) contain no per-product data
  in text or image; no parser can invent it. terbium says so rather than guessing.
- Implicit-attribute extraction from images is only as good as the frontier vision
  model of the day; we keep it opt-in and confidence-scored.
- Normalization taxonomies (color, material) need curation per market; start
  small and expand from the evaluation set.
