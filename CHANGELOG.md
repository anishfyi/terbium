# Changelog

Full history, including releases before this file existed: https://velofy.co/terbium/changelog/

## 0.10.0 (2026-09-30)

First tagged GitHub release. PyPI serves 0.9.7 until the 0.10.0 upload is made; until then install from the wheel attached to the GitHub release or from the `v0.10.0` tag.

### Added

- Document classification (`terbium.classify`): catalog, lookbook, transaction, resume, table, deck or unknown, which picks the schema. `--type` and `doc_type=` override it.
- Transaction schema for invoices, bills, receipts, purchase orders and quotes, with summary and line item records.
- Resume schema with a candidate header and sectioned records.
- CSV, self-contained HTML and terminal table output for every lane. New CLI flags `--type`, `--html` and `--open`; the CLI routes invoices and resumes to the records view.
- Image adapter for PNG, JPG, JPEG, WEBP and TIFF through local Tesseract OCR.
- Picture-heavy catalogues: per-page lookbook detection, proximity-scored captions, dense grids and one-photo pages. The catalog table gains a Dimensions column.
- AI providers GPT (OpenAI), Kimi (Moonshot) and Grok (xAI) through the OpenAI-compatible client, with extras `openai`, `kimi` and `grok`. Claude stays the default when several keys are set.
- Exports `terbium.records_to_csv`, `terbium.render_html`, `terbium.render_terminal_table`.

### Fixed

- The invoice and receipt AI step now runs. It looked for `header` records while the parser emits `summary` records, so it never filled anything. It now fills missing summary fields, adds a summary when there is none, and adds AI line items only when the parser found none.
- `ParsedDocument.used_ai` is True only when a model call returned a response. Before, any transaction parse with a key set reported AI use.
- Terminal tables truncate header cells to the column width, truncated cells no longer run two characters past their column, and column widths are budgeted for the box borders, so columns line up.
- The catalog message no longer suggests `ocr=True` when Tesseract is not installed; it says to install Tesseract or use the AI vision lane.
- OpenAI o-series models (the `opus` tier maps to `o3-mini`) are called with `max_completion_tokens` instead of `max_tokens`, which the openai SDK documents as incompatible with o-series models. The `openai`, `kimi`, `grok` and `ai` extras now require `openai>=1.45`, the first SDK version with that parameter.

### Known issues

- The `opus` tier on OpenAI (`o3-mini`) may still reject image input for the vision lane; not verified against the API.
- Model IDs for each provider are taken from source and not verified against the provider APIs.
- The Gemini lane uses `google-generativeai`, which Google has superseded with `google-genai`.
