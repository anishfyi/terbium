"""``terbium <file>`` - parse documents from the command line.

Auto-classifies the input, prints a terminal table by default, and can write CSV
or HTML. Catalog behaviour is unchanged for catalog inputs. Invoices and resumes
detected under ``--type auto`` route to the records view. No AI unless --ai.

    terbium catalogue.pdf                 # print the table (images -> catalogue_images/)
    terbium catalogue.pdf --csv out.csv   # + write the CSV
    terbium invoice.pdf                   # auto-detects transaction records
    terbium invoice.pdf --type transaction
    terbium resume.pdf --type resume --html out.html
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from . import __version__
from .api import parse, supported_extensions
from .catalog import CATALOG_COLUMNS, build_catalog, to_catalog_csv
from .classify import DOC_TYPES
from .harness import AI
from .render import render_html, render_terminal_table, to_csv


def _records_to_rows(doc):
    rows = []
    for r in doc.records:
        row = {"sku": r.sku or "", "confidence": f"{r.confidence:.2f}"}
        row.update(r.fields)
        rows.append(row)
    return rows


def _record_table_headers(rows):
    keys = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    return keys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="terbium",
        description="Parse a document into structured records. Auto-classifies "
                    "catalogues, invoices, resumes, and tables. No AI unless --ai.",
    )
    ap.add_argument("file", help="path to a " + "/".join(supported_extensions()) + " file")
    ap.add_argument("--type", default="auto", choices=["auto", *DOC_TYPES],
                    help="document type override (default: auto)")
    ap.add_argument("--csv", metavar="OUT", help="write records as CSV (path or -)")
    ap.add_argument("--html", metavar="OUT", help="write self-contained HTML (path or -)")
    ap.add_argument("--open", action="store_true", help="open --html output in a browser")
    ap.add_argument("--images", metavar="DIR", help="dir for extracted images (default: <file>_images)")
    ap.add_argument("--no-images", action="store_true", help="do not extract product images")
    ap.add_argument("--limit", type=int, default=20, help="rows to show in the terminal (0 = all)")
    ap.add_argument("--records", action="store_true", help="show parsed records instead of catalog table")
    ap.add_argument("--schema", default=None,
                    help="schema for --records: product/generic/furniture/transaction/resume")
    ap.add_argument("--json", metavar="OUT", help="(--records) write records as JSON (path or -)")
    ap.add_argument("--ai", action="store_true", help="opt in to the AI pass (off by default)")
    ap.add_argument("--tier", choices=["haiku", "sonnet", "opus"], help="pin the AI model tier")
    ap.add_argument("--version", action="version", version=f"terbium {__version__}")
    args = ap.parse_args(argv)

    ai = AI(force_tier=args.tier) if args.ai else None
    doc_type = args.type
    schema = args.schema

    # ---- parsed records view (explicit --records or non-catalog types) ----
    _catalog_types = ("catalog", "lookbook", "table", "deck", "unknown")
    use_catalog = (
        not args.records
        and doc_type in ("catalog", "lookbook")
        and (schema is None or schema in ("product", None))
    )
    if doc_type == "auto" and not args.records and (schema is None or schema in ("product", None)):
        from .documents import get_adapter
        from .classify import classify as classify_doc

        pages = get_adapter(args.file).parse(args.file)
        detected, _ = classify_doc(pages)
        doc_type = detected
        use_catalog = detected in _catalog_types

    if not use_catalog:
        if schema is None:
            schema = "product" if doc_type in ("catalog", "lookbook", "table") else None
        doc = parse(args.file, schema=schema, ai=ai, doc_type=doc_type)
        rows = _records_to_rows(doc)
        headers = _record_table_headers(rows)

        if args.json:
            payload = doc.to_json()
            if args.json == "-":
                print(payload)
            else:
                with open(args.json, "w", encoding="utf-8") as f:
                    f.write(payload)
                print(f"wrote {len(doc.records)} records -> {args.json}", file=sys.stderr)
            return 0

        if args.csv:
            text = to_csv(doc.records)
            if args.csv == "-":
                sys.stdout.write(text)
            else:
                to_csv(doc.records, args.csv)
                print(f"wrote {len(doc.records)} records -> {args.csv}", file=sys.stderr)

        if args.html:
            html_text = render_html(doc.records)
            if args.html == "-":
                sys.stdout.write(html_text)
            else:
                with open(args.html, "w", encoding="utf-8") as f:
                    f.write(html_text)
                print(f"wrote HTML -> {args.html}", file=sys.stderr)
                if args.open:
                    webbrowser.open(f"file://{os.path.abspath(args.html)}")

        shown = rows if args.limit == 0 else rows[: args.limit]
        table_rows = [[r.get(h, "") for h in headers] for r in shown]
        dtype = getattr(doc, "doc_type", doc_type)
        print(f"terbium {__version__}  ·  {doc.source_kind}  ·  {dtype}  ·  {doc.stats.total} records")
        print(render_terminal_table(headers, table_rows))
        if args.limit and doc.stats.total > args.limit:
            print(f"... and {doc.stats.total - args.limit} more (use --limit 0 for all)")
        return 0

    # ---- catalog table (default for catalog inputs) -------------------------
    ext = os.path.splitext(args.file)[1].lower().lstrip(".")
    images_dir = None
    if not args.no_images:
        images_dir = args.images or (
            os.path.splitext(args.file)[0] + "_images" if ext in ("pdf", "pptx") else None
        )
    rows_data = build_catalog(args.file, images_dir=images_dir, ai=ai)

    if args.csv:
        if args.csv == "-":
            sys.stdout.write(to_catalog_csv(rows_data))
            return 0
        to_catalog_csv(rows_data, args.csv)
        print(f"wrote {len(rows_data)} products -> {args.csv}", file=sys.stderr)

    if args.html:
        html_text = render_html(rows_data)
        if args.html == "-":
            sys.stdout.write(html_text)
        else:
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(html_text)
            print(f"wrote HTML -> {args.html}", file=sys.stderr)
            if args.open:
                webbrowser.open(f"file://{os.path.abspath(args.html)}")

    head = f"terbium {__version__}  ·  {args.file}  ·  {len(rows_data)} products"
    if images_dir:
        head += f"  ·  images -> {images_dir}/"
    print(head)
    shown = rows_data if args.limit == 0 else rows_data[: args.limit]
    table = [[r.get("sku") or "", r.get("name") or "", r.get("materials") or "",
              r.get("dimensions") or "", r.get("image") or "", r.get("page") or ""] for r in shown]
    print(render_terminal_table(CATALOG_COLUMNS, table))
    if args.limit and len(rows_data) > args.limit:
        print(f"... and {len(rows_data) - args.limit} more (use --limit 0 for all, or --csv out.csv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
