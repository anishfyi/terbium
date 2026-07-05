# The catalog table

terbium's headline job: point it at any vendor catalogue and get back a table of
products, one row each, with the **name**, the **SKU**, the **materials or
ingredients**, and the path to the product's **image**. Then write it to CSV.

```python
import terbium

rows = terbium.build_catalog("vendor_catalogue.pdf", images_dir="images/")
terbium.to_catalog_csv(rows, "catalogue.csv")
```

`rows` is a list of dicts:

```python
{"sku": "RG-1001", "name": "Anatolia Kilim",
 "materials": "wool", "image": "Anatolia_Kilim.jpeg", "page": 12}
```

and `catalogue.csv` has exactly the columns you would hand to a buyer or a PIM:

```
SKU,Name,Materials/Ingredients,Image,Page
,Kyoto Bedside Table,,Kyoto_Bedside_Table.jpeg,2
RG-1001,Anatolia Kilim,wool,Anatolia_Kilim.jpeg,12
```

## From the terminal (no AI)

```bash
terbium catalogue.pdf                    # print the table; images -> catalogue_images/
terbium catalogue.pdf --csv out.csv      # + write the CSV
terbium catalogue.pdf --csv -            # print raw CSV to stdout instead
terbium catalogue.pdf --limit 0          # show every row, not just the first 20
terbium prices.xlsx  --no-images         # a pricelist: table only, no image extraction
terbium catalogue.pdf --records          # raw parsed records instead of the table
```

`terbium <file>` prints an aligned table (SKU, Name, Materials/Ingredients, Image,
Page) and, for a PDF or PPTX, extracts the photos to `<file>_images/`. It uses no
AI unless you add `--ai`. Example:

```
terbium 0.9.3  ·  catalogue.pdf  ·  124 products  ·  images -> catalogue_images/
SKU     | Name           | Materials/Ingredients | Image                | Page
--------+----------------+-----------------------+----------------------+-----
MRP-962 | Aur 152 Peach  | wool                  | Aur_152_Peach.jpeg   | 10
```

## How it works

For an image-bearing PDF, every product **photo anchors a row**. terbium:

1. extracts the photo (skipping logos, icons, and banners) into `images_dir`,
2. names the row from the **label beneath the photo**, or the page's heading when
   there is no caption,
3. mines the nearby text for a **SKU** (a real code, not a page number or price)
   and a **materials/ingredients** line (a `Material:` label, a `78% wool`
   composition, or material words in the description like "solid mango wood").

For a pricelist-style catalogue with no photos, rows come from the product table
instead (`name`, `sku`, `materials` from the columns), with `image` left blank.

## When the layout hides things: the AI pass

Clean catalogues (a labelled photo grid) come out complete with no key. Visual
brochures bury the name in a range title and the material in a paragraph. Pass an
`AI` to read each product photo **plus** the page text and fill what is missing:

```python
rows = terbium.build_catalog(
    "brochure.pdf", images_dir="images/", ai=terbium.AI()   # reads ANTHROPIC_API_KEY
)
```

The AI pass only fills blanks, never overwrites a value the deterministic pass was
sure of, and is told not to invent a SKU or a material that is not supported by
the image or the text.

### It tells you when it needs the key

When the deterministic pass leaves a meaningful share of the table blank and no
AI is in play, `build_catalog` does not stay quiet. It prints the blank-field
census, names the image-only pages (where the data lives in the photos, not the
text), and recommends the tier:

```
terbium: 8/121 products have a name, 0 a SKU, 9 materials/ingredients.
82 page(s) are image-only (1, 5, 6, 7, 8, ...) - the data lives in the photos, not the text.
-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   recommended tier: Opus (vision)
```

Silence it with `build_catalog(..., announce=False)`, or ask for the message
yourself with `terbium.catalog.catalog_escalation(rows)`.

## Proven across categories

A representative lookbook PDF was generated for each of six product categories
(real embedded photos + name/SKU/materials captions) and run through
`build_catalog` with no AI key. Every field was recovered for every product:

| category | products | name | sku | materials | image |
|---|---|---|---|---|---|
| rugs | 4 | 4 | 4 | 4 | 4 |
| lamps | 4 | 4 | 4 | 4 | 4 |
| bags | 4 | 4 | 4 | 4 | 4 |
| handbags | 4 | 4 | 4 | 4 | 4 |
| cushions | 4 | 4 | 4 | 4 | 4 |
| handwash | 4 | 4 | 4 | 4 | 4 |
| **total** | **24** | **24** | **24** | **24** | **24** |

Reproduce with `python eval/category_bench.py`. This measures the deterministic
engine on clean lookbook layouts; messy real-world brochures are where the AI pass
earns its place (below).

## On real vendor catalogues (six categories, no AI key)

Six genuine vendor catalogue PDFs, one per category, downloaded from the open web
and run through `build_catalog` with no key. 1,010 products in total:

| category (real source) | products | name | image | sku | materials |
|---|---|---|---|---|---|
| furniture (Trampoline) | 70 | 70 | 70 | 10 | 18 |
| rugs (The Rug Furnish) | 124 | 97 | 124 | 103 | 41 |
| lamps (Sahil & Sarthak, 227 pp) | 484 | 415 | 484 | 229 | 191 |
| cushions (Domkapa) | 121 | 40 | 121 | 8 | 66 |
| handbags (Zoosch) | 183 | 108 | 183 | 59 | 112 |
| handwash (English Soap Co) | 28 | 0 | 28 | 0 | 0 |
| **total** | **1010** | **730** | **1010** | **409** | **428** |

What this says honestly:

- **Image extraction is the solved core: 1010/1010.** Every product on every real
  catalogue got its photo pulled and linked.
- **Name 72%, SKU 40%, materials 42%** deterministically. Strong where the
  catalogue prints them beside the photo (lamps: real codes like `SSVSNL26`, rugs:
  `MRP-962`), thin where it does not. A SKU count below the product count usually
  means that catalogue simply does not print a per-product code.
- **The handwash brochure is the honest floor: images yes, text zero.** Its names
  and ingredients are set as stylised artwork, not selectable text. This is exactly
  what the AI pass is for: give it a key and a vision model reads the product photo
  plus the page to recover the name and ingredients.

So the deterministic engine owns the image and does well on text where the layout
is clean; the AI pass is what carries the messy, stylised catalogues the rest of
the way. That split is the design, not a gap.
