# Pulling out images

Text is only half a catalogue. `terbium.export_images` extracts the actual
product photos and, for lookbooks, names each file after the product beneath it.

```python
import terbium
manifest = terbium.export_images("lookbook.pdf", "out/")
```

```bash
terbium lookbook.pdf --images out/     # writes photos + out/manifest.csv
```

## What you get

Files land in `out/` named after the product (`Kyoto_Bedside_Table.jpeg`) for
lookbooks, or by page (`page060.jpeg`) when there is no label. The returned
manifest, one row per image, carries the qualities worth having:

| Field | Meaning |
|---|---|
| `product`, `collection` | the label under the photo and its group (lookbooks) |
| `page` | source page (1-based) |
| `file` | the written filename |
| `format` | `jpeg` / `png` (the embedded encoding, extracted losslessly) |
| `width_px`, `height_px` | true pixel dimensions |
| `colorspace` | `RGB` / `CMYK` / `Gray` |
| `dpi` | effective resolution at its placed size |
| `dominant_color` | average colour as hex, a cheap read on the finish |
| `bbox` | position on the page (used to bind photo to label) |

## How it decides what to keep

- **Only photos.** Icons and swatches are skipped, and so are thin banner strips
  and slivers (shorter side under `min_side` px, aspect ratio over `max_aspect`).
- **No repeated logos.** An image that recurs across many pages (a watermark or
  brand mark) is detected and dropped, so you do not get the logo 80 times.
- **Association.** Each photo binds to the label sitting directly below it and
  horizontally aligned, which is how the files get product names.

Tune with `export_images(path, out, only_photos=..., min_side=..., max_aspect=...,
associate=..., dedupe_repeats=...)`.

## Bytes come from PyMuPDF

terbium extracts image bytes with PyMuPDF (already a dependency), which returns a
ready-to-save JPEG/PNG. pdfplumber is excellent for image position and metadata
and for cropping a region to a PNG, but pulling raw bytes through it means
decoding PDF filters yourself, so terbium does not need it as a dependency.
