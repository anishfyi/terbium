# Quickstart

## Install

```bash
pip install terbium-parse
```

Optional AI lanes (only needed if you want terbium to resolve hard pages):

```bash
pip install "terbium-parse[anthropic]"   # Claude (preferred)
pip install "terbium-parse[openai]"      # GPT
pip install "terbium-parse[kimi]"        # Kimi
pip install "terbium-parse[grok]"        # Grok
pip install "terbium-parse[gemini]"      # Gemini vision
pip install "terbium-parse[ai]"          # all lanes
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
| `schema` | `"generic"` (default), `"product"`, `"furniture"`, `"transaction"`, `"resume"`, or a `Schema` instance |
| `doc_type` | `"auto"` (default) or `catalog`/`transaction`/`resume`/... override |
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
terbium catalogue.pdf                    # auto-classify; print table + extract images
terbium catalogue.pdf --csv out.csv      # write CSV
terbium catalogue.pdf --schema furniture
terbium report.xlsx --json out.json
terbium invoice.pdf --type transaction   # force transaction lane
terbium invoice.pdf --csv rows.csv --html report.html   # any lane: csv + self-contained report
terbium resume.pdf --html out.html --open
terbium deck.pptx --ai --tier opus       # enable AI, pin the tier
terbium lookbook.pdf --images out/       # extract product photos
terbium scan.png                         # image file via OCR adapter
```

See [documents.md](documents.md) for transaction/resume lanes and output flags.
The same call reads catalogues, invoices, receipts, and resumes; see
[TAXONOMY.md](TAXONOMY.md) for the full map of document types and formats.

## Pulling out images

To export the actual product photos (named after each product), use
`terbium.export_images(path, out_dir)` or `--images`. See [images.md](images.md).
