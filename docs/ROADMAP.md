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

## The moat (why terbium wins this niche)

1. **Product records, not markdown.** Typed rows with SKU + attributes + a linked
   image file, not a wall of text to re-parse.
2. **Category-agnostic attributes.** A bag gets capacity, a lamp gets wattage, a
   rug gets pile, a handwash gets volume and scent, without a hand-written schema
   per category. The AI infers explicit and implicit attributes from text + image
   (the technique Shopify, Amazon, and Mirakl now ship).
3. **Images linked to products.** We already extract photos named by product. That
   is a commerce deliverable no general parser gives you.
4. **Deterministic-first cost model.** We solve what geometry can solve for free
   and call an LLM only on what is genuinely hard, versus tools that bill an LLM
   per page. Cheaper and faster at catalogue scale.
5. **Confidence + honest escalation.** Every record carries a score; the system
   says what it is unsure about instead of hallucinating a spec.

## Architecture: deterministic core, AI as a layer

```
  file (pdf/pptx/xlsx/csv)
        |
  [1] ADAPT + RECONSTRUCT   generic tables, label grids, text blocks, images   (done)
        |
  [2] PRODUCT MAP           category-agnostic columns -> product fields         (building now)
        |  confidence gate
  [3] AI ENRICH (opt-in)    normalize + fill implicit attributes + read images  (next)
        |
  [4] NORMALIZE             units, currency, color/material taxonomy            (next)
        |
  product records + linked images + manifest
```

- **[1] is shipped** (0.4.0): content-agnostic table detector, label grids for
  lookbooks, image extraction named by product, image-only escalation.
- **[2] Product map (this iteration).** A `product` schema that maps any table's
  columns to a universal product record by header meaning (sku/name/price/size/
  color/material/qty/...), everything else preserved as attributes. Works offline,
  across every category, for the common case: a row-per-product pricelist.
- **[3] AI enrich (next).** When a key is present, hand each product block plus its
  photo to a routed model and get back normalized fields and the implicit
  attributes (style, pattern, material read from the image). Confidence-gated, so
  it only runs where the deterministic map is unsure. Degrades to escalation.
- **[4] Normalize.** Dimensions to a common unit, prices to {amount, currency},
  colors and materials to controlled vocabularies, so records are feed-ready.

## Model routing (per 2026 benchmarks)

Frontier models lead on hard document work, but the premium-to-budget gap is only
~10 points, so route by difficulty, not by default:
- trivial / clean table -> deterministic only, no model.
- moderate -> a fast model (Haiku / Gemini Flash).
- hard, image-only, or implicit-attribute reads -> a frontier model (Opus /
  Gemini 3 Pro / GPT-5.1), which the benchmarks show is worth it there.

## Proving "best": an evaluation harness

"Best" has to be measured, not claimed.
- A golden set per category (furniture, rugs, lamps, bags, cushions, handwash):
  the source file plus the correct product records and attributes.
- Metrics: record recall/precision, per-attribute accuracy, image-to-product
  linkage accuracy, and cost/page.
- Run terbium (deterministic and with-AI) against LlamaParse, Docling, and a
  raw vision-LLM baseline on the same golden set, and publish the table.
- Adopt OmniDocBench-style rigor for the table-reconstruction sub-problem.

## Phased plan

| Phase | Deliverable | State |
|---|---|---|
| 0 | Generic engine: tables, labels, images, confidence, escalation | done (0.4.0) |
| 1 | Universal `product` schema (category-agnostic column mapping) | done (0.5.0) |
| 2 | AI enrich layer: implicit attributes + vision reads | done (0.6.0) |
| 3 | Normalization: units, currency, color/material taxonomies | done (0.7.0) |
| 4 | Evaluation harness + public benchmark vs the field | next |
| 5 | Feed exporters (Shopify CSV, Google Merchant, generic PIM JSON) | after 4 |

## Risks and honest limits

- Some catalogues (like the Fable Room teaser deck) contain no per-product data
  in text or image; no parser can invent it. terbium says so rather than guessing.
- Implicit-attribute extraction from images is only as good as the frontier vision
  model of the day; we keep it opt-in and confidence-scored.
- Normalization taxonomies (color, material) need curation per market; start
  small and expand from the evaluation set.
