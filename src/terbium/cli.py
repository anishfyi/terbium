"""``terbium <file>`` - parse a catalogue from the command line.

By default it builds the catalog table (SKU, name, materials/ingredients, image),
prints it to the terminal, and can write it to CSV. No AI is used unless you pass
``--ai``.

    terbium catalogue.pdf                 # print the table (images -> catalogue_images/)
    terbium catalogue.pdf --csv out.csv   # + write the CSV
    terbium catalogue.pdf --csv -          # print raw CSV to stdout instead
    terbium prices.xlsx --no-images        # a pricelist, no image extraction
    terbium catalogue.pdf --records        # raw parsed records instead of the table
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

from . import __version__
from .api import parse, supported_extensions
from .catalog import CATALOG_COLUMNS, build_catalog, to_catalog_csv
from .harness import AI


def _render_table(headers, rows) -> str:
    """A plain, aligned terminal table that fits the current width."""
    cols = len(headers)
    w = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            w[i] = max(w[i], len(str(r[i])))
    term = shutil.get_terminal_size((120, 20)).columns
    guard = 0
    while sum(w) + 3 * (cols - 1) > term and guard < 10000:
        j = w.index(max(w))
        if w[j] <= 8:
            break
        w[j] -= 1
        guard += 1

    def cell(s, width):
        s = str(s)
        return s if len(s) <= width else s[: max(1, width - 1)] + "…"

    out = [" | ".join(str(h).ljust(w[i]) for i, h in enumerate(headers))]
    out.append("-+-".join("-" * w[i] for i in range(cols)))
    for r in rows:
        out.append(" | ".join(cell(r[i], w[i]).ljust(w[i]) for i in range(cols)))
    return "\n".join(out)


def _records_csv(doc) -> str:
    import csv as _csv
    import io

    keys = []
    for r in doc.records:
        for k in r.fields:
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["sku", "confidence", *keys])
    for r in doc.records:
        w.writerow([r.sku or "", f"{r.confidence:.2f}", *[r.fields.get(k, "") for k in keys]])
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="terbium",
        description="Parse a catalogue into a table of products (SKU, name, "
                    "materials/ingredients, image) and/or CSV. No AI unless --ai.",
    )
    ap.add_argument("file", help="path to a " + "/".join(supported_extensions()) + " file")
    ap.add_argument("--csv", metavar="OUT", help="write the table as CSV (a path, or - for stdout)")
    ap.add_argument("--images", metavar="DIR", help="dir for extracted images (default: <file>_images)")
    ap.add_argument("--no-images", action="store_true", help="do not extract product images")
    ap.add_argument("--limit", type=int, default=20, help="rows to show in the terminal (0 = all)")
    ap.add_argument("--records", action="store_true", help="show raw parsed records instead of the catalog table")
    ap.add_argument("--schema", default="product", help="schema for --records: product/generic/furniture")
    ap.add_argument("--json", metavar="OUT", help="(--records) write records as JSON (a path, or -)")
    ap.add_argument("--ai", action="store_true", help="opt in to the AI pass (off by default)")
    ap.add_argument("--tier", choices=["haiku", "sonnet", "opus"], help="pin the AI model tier")
    ap.add_argument("--version", action="version", version=f"terbium {__version__}")
    args = ap.parse_args(argv)

    ai = AI(force_tier=args.tier) if args.ai else None

    # ---- raw records view -------------------------------------------------
    if args.records:
        doc = parse(args.file, schema=args.schema, ai=ai)
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
            text = _records_csv(doc)
            if args.csv == "-":
                sys.stdout.write(text)
                return 0
            with open(args.csv, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            print(f"wrote {len(doc.records)} records -> {args.csv}", file=sys.stderr)
        shown = doc.records if args.limit == 0 else doc.records[: args.limit]
        rows = [[r.sku or "-", f"{r.confidence:.2f}", str(r.fields)] for r in shown]
        print(f"terbium {__version__}  ·  {doc.source_kind}  ·  {doc.stats.total} records")
        print(_render_table(["SKU", "conf", "fields"], rows))
        if args.limit and doc.stats.total > args.limit:
            print(f"... and {doc.stats.total - args.limit} more (use --limit 0 for all)")
        return 0

    # ---- catalog table (default) -----------------------------------------
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

    head = f"terbium {__version__}  ·  {args.file}  ·  {len(rows_data)} products"
    if images_dir:
        head += f"  ·  images -> {images_dir}/"
    print(head)
    shown = rows_data if args.limit == 0 else rows_data[: args.limit]
    table = [[r.get("sku") or "", r.get("name") or "", r.get("materials") or "",
              r.get("image") or "", r.get("page") or ""] for r in shown]
    print(_render_table(CATALOG_COLUMNS, table))
    if args.limit and len(rows_data) > args.limit:
        print(f"... and {len(rows_data) - args.limit} more (use --limit 0 for all, or --csv out.csv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
