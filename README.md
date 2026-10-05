<div align="center">

<a href="https://velofy.co/terbium/"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/velofy/terbium/main/assets/tile-dark.svg">
    <img alt="terbium" src="https://raw.githubusercontent.com/velofy/terbium/main/assets/tile-light.svg" width="360">
  </picture></a>

# terbium

**Business documents in. Clean rows out.**

</div>

terbium parses business documents (vendor catalogues first, plus invoices, receipts, resumes, price lists and decks) into clean rows. It rebuilds structure from the position of every word, scores its own confidence, and only calls an AI model when the algorithm cannot be sure.

[![License: MIT](https://img.shields.io/badge/license-MIT-000000.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-000000.svg)](pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/terbium-parse?color=000000&label=pypi)](https://pypi.org/project/terbium-parse/)

**Documentation: https://velofy.co/terbium/**

[Docs](https://velofy.co/terbium/) · [Quickstart](https://velofy.co/terbium/quickstart/) · [Trove](https://github.com/anishfyi/trove)

---

<h3 align="center">Sponsors</h3>

<p align="center"><strong>Primary sponsor</strong></p>

<p align="center">
  <a href="https://go.nodemaven.com/terbiumreadmeoct" title="NodeMaven: best proxy for web scraping and automation">
    <img src="https://raw.githubusercontent.com/anishfyi/terbium/main/assets/sponsors/nodemaven-banner.jpg" alt="NodeMaven: best proxy for web scraping and automation with the highest quality IP" width="720">
  </a>
</p>

**[NodeMaven](https://go.nodemaven.com/terbiumreadmeoct)**: the most efficient proxy provider for web scraping and automation, with the highest quality IPs on the market.

Why [NodeMaven](https://go.nodemaven.com/terbiumreadmeoct)?

- ZIP targeting
- 99.9% uptime
- IP filtering: every proxy has a fraud score under 97%
- No KYC required
- Free tools: Proxy Bandwidth Checker, Meta Tag Checker, IP Lookup and more

Codes for terbium users: `TERBIUM35` for 35% off mobile and residential proxies, `TERBIUM40` for 40% off ISP (static) proxies.

---

## Install

```bash
pip install terbium-parse
```

The PyPI name is `terbium-parse`; you `import terbium`, and the command is `terbium`. (The PyPI project named `terbium` is unrelated.)

terbium 0.10.0 is released on GitHub, but PyPI still serves 0.9.7 until the 0.10.0 upload is made, so `pip install terbium-parse` gives you 0.9.7 today. This README describes 0.10.0, which adds invoices, receipts, resumes, image files, HTML output and more AI providers. To get 0.10.0 now, install the wheel attached to the GitHub release, or the tag:

```bash
pip install "https://github.com/velofy/terbium/releases/download/v0.10.0/terbium_parse-0.10.0-py3-none-any.whl"
# or
pip install "git+https://github.com/velofy/terbium.git@v0.10.0"
```

Optional AI lanes: `pip install "terbium-parse[anthropic]"` (or `openai`, `kimi`, `grok`, `gemini`, or `ai` for all). OCR of images and image-only pages needs a local `tesseract` binary. Details: [Installation](https://velofy.co/terbium/installation/).

## Example

Point it at a vendor catalogue and get a table of products, each with its name, SKU, materials or ingredients, dimensions and image. Then a CSV.

```python
import terbium

rows = terbium.build_catalog("vendor_catalogue.pdf", images_dir="images/")
terbium.to_catalog_csv(rows, "catalogue.csv")
# rows: {"sku": "RG-1001", "name": "Anatolia Kilim", "materials": "wool",
#        "dimensions": None, "image": "Anatolia_Kilim.jpeg", "page": 12}
```

The same engine reads other documents:

```python
doc = terbium.parse("invoice.pdf")                     # line items, totals, vendor
cv = terbium.parse("maria_cv.pdf", doc_type="resume")  # sections, experience, skills
print(doc.stats)   # Stats(total=..., confident=..., ambiguous=...)
```

```bash
terbium catalogue.pdf --csv out.csv                    # product table + photos, no AI
terbium invoice.pdf --csv rows.csv --html report.html  # CSV + self-contained report
```

## Features

- **Structure from geometry.** Running headers are stripped, two-page spreads split, and columns, rows and matrices rebuilt from word positions. The table detector is content-agnostic.
- **Catalog table.** Each product photo anchors a row; the name, SKU, materials and dimensions are mined from nearby text, and the photo is extracted and named after the product.
- **Many document types.** Automatic classification into catalogue, lookbook, transaction, resume, table or deck, with `--type` to override.
- **Formats.** PDF, PPTX, XLSX, CSV, and PNG, JPG, WEBP or TIFF images through local OCR.
- **Confidence on every record.** Each record carries a 0.05 to 1.0 score and the reasons behind it.
- **AI only where needed.** Hard tables go to a routed model tier (Haiku, Sonnet or Opus class) across Claude (default), GPT, Kimi, Grok and Gemini. With no key, terbium prints which pages need help and which tier it recommends.
- **Feeds.** Normalized colour, material and dimension fields, plus Shopify CSV and PIM JSON exporters.

## Documentation

- [Overview](https://velofy.co/terbium/)
- [Installation](https://velofy.co/terbium/installation/) and [Quickstart](https://velofy.co/terbium/quickstart/)
- [The catalog table](https://velofy.co/terbium/catalog/) and [Pulling out images](https://velofy.co/terbium/images/)
- [Invoices, receipts and resumes](https://velofy.co/terbium/documents/)
- [File formats](https://velofy.co/terbium/formats/) and [Schemas](https://velofy.co/terbium/schemas/)
- [Confidence and escalation](https://velofy.co/terbium/confidence/)
- [AI lane and routing](https://velofy.co/terbium/ai-and-routing/)
- [Normalization and feeds](https://velofy.co/terbium/feeds/)
- [CLI reference](https://velofy.co/terbium/cli/) and [Python API reference](https://velofy.co/terbium/python-api/)
- [Document taxonomy](https://velofy.co/terbium/taxonomy/)
- [Evaluation](https://velofy.co/terbium/evaluation/) and [Changelog and status](https://velofy.co/terbium/changelog/)

Developer notes stay in this repository: [docs/DESIGN.md](docs/DESIGN.md), [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/TAXONOMY.md](docs/TAXONOMY.md).

## Contributing

Issues and pull requests are welcome at https://github.com/velofy/terbium. To work on the code:

```bash
git clone https://github.com/velofy/terbium.git
cd terbium
pip install -e ".[dev]"
python -m pytest -q
python eval/category_bench.py
```

## License

MIT. Built by [anishfyi](https://github.com/anishfyi). See [LICENSE](LICENSE).

<div align="center"><sub>terbium · Tb · 65</sub></div>
