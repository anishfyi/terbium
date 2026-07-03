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

## Two real catalogues

- A labelled lookbook deck (photo grid, a name under each): **70 products, every
  one with its name and its own image file**, deterministically, no key.
- A visual brochure (full-bleed photos, range titles, prose descriptions):
  the range names (Virasat, Eterna, Nordic, ...) and images come out
  deterministically; per-product names, SKUs, and materials are what the AI pass
  is for.
