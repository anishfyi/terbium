# Documents: transactions, resumes, and universal output

terbium 0.10.0 extends the parser beyond catalogues to invoices, receipts,
resumes, and image files, with universal CSV/HTML/terminal output.

## Auto-classification

After adapting a file to pages, terbium scores page-level signals (image density,
keyword hits, date/currency density, layout shape) and picks a document type:

| Type | Typical input |
|------|---------------|
| `catalog` | row-per-product pricelist, SKU tables |
| `lookbook` | image grid with product names |
| `transaction` | invoice, bill, receipt, PO, quote |
| `resume` | CV with experience/education sections |
| `table` | financial or data tables |
| `deck` | PPTX presentation |
| `unknown` | low-confidence fallback |

Override with `--type` or `doc_type=` in `terbium.parse()`. Catalog inputs keep
the existing `build_catalog` path when auto-classified as catalog/lookbook.

```python
import terbium

doc = terbium.parse("invoice.pdf")              # auto -> transaction schema
doc = terbium.parse("resume.pdf", doc_type="resume")
```

## Transaction lane

One schema covers invoice, bill, receipt, PO, and quote via `FIELD_SYNONYMS`
(same pattern as the product schema). Header fields (number, date, vendor,
customer, tax id) and line items (description, qty, unit price, amount) are
extracted from tables and key-value geometry (`layout/forms.py`).

```bash
terbium invoice.pdf --type transaction --csv invoice.csv
terbium receipt.pdf --records --schema transaction
```

With `--ai`, the transaction AI lane (`harness/transaction_ai.py`) fills missing
fields via Anthropic-first routing.

## Resume lane

Candidate header (name, email, phone, links) plus sectioned records for
experience, education, skills, projects, and certifications. Each row carries a
`section` field for flat CSV export.

```bash
terbium resume.pdf --type resume --html resume.html --open
```

## Universal output

All document types share the render package:

| Module | Role |
|--------|------|
| `render/terminal.py` | Unicode box table with fallback chain (never crashes) |
| `render/html.py` | Self-contained HTML (Inter via Google Fonts, system-ui fallback) |
| `render/csv_out.py` | Generic `to_csv(records)` - union of field keys, stable order |

```bash
terbium report.pdf --csv out.csv
terbium report.pdf --html out.html --open
terbium report.pdf --limit 0          # show all rows in terminal
```

## Image files

PNG, JPG, JPEG, WEBP, and TIFF files are adapted to a single page. Words come
from the local Tesseract bridge (`layout/ocr.py`) when available.

```bash
terbium scan.png --type auto
```

## CLI flags (0.10.0)

| Flag | Meaning |
|------|---------|
| `--type auto\|catalog\|transaction\|resume\|...` | document type override |
| `--csv OUT` | write CSV (`-` for stdout) |
| `--html OUT` | write self-contained HTML |
| `--open` | open `--html` in a browser |
| `--schema` | schema for `--records` mode |
| `--records` | raw parsed records instead of catalog table |
| `--json` | JSON output (with `--records`) |
| `--images` / `--no-images` | image extraction (catalog path) |
| `--ai` / `--tier` | opt-in AI pass |

Existing flags behave as before for catalog inputs.
