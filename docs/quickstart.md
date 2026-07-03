# Quickstart

## Install

```bash
pip install terbium-parse
```

Optional AI lanes (only needed if you want terbium to resolve hard pages):

```bash
pip install "terbium-parse[anthropic]"   # Claude
pip install "terbium-parse[gemini]"      # Gemini vision
pip install "terbium-parse[ai]"          # both
```

## Parse a file

```python
import terbium

doc = terbium.parse("catalogue.pdf")
print(doc.stats)                 # Stats(total=..., confident=..., ambiguous=...)

for r in doc.records:
    print(r.sku, r.confidence, r.fields)
```

`terbium.parse` accepts:

| Argument | Meaning |
|---|---|
| `path` | the PDF / PPTX / XLSX / CSV file |
| `schema` | `"generic"` (default) or `"furniture"`, or a `Schema` instance |
| `ai` | `terbium.AI(...)`, `True` (use env keys), or `None` (off) |
| `threshold` | confidence below which a record counts as ambiguous (default `0.72`) |
| `announce` | print the escalation message to stderr when a key would help (default `True`) |

## The result

`ParsedDocument` gives you:

- `doc.records` - every extracted record, each with `.sku`, `.fields`, `.confidence`, `.reasons`, `.origin`
- `doc.confident_records` / `doc.ambiguous_records`
- `doc.stats` - totals
- `doc.escalation` - the "add a key" message, or `None`
- `doc.to_json()` - serialize everything

## Command line

```bash
terbium catalogue.pdf --schema furniture
terbium report.xlsx --json out.json
terbium deck.pptx --ai --tier opus       # enable AI, pin the tier
terbium lookbook.pdf --images out/       # extract product photos + manifest.csv
```

## Pulling out images

To export the actual product photos (named after each product), use
`terbium.export_images(path, out_dir)` or `--images`. See [images.md](images.md).
