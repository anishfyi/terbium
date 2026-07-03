"""`terbium <file>` - parse from the command line."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .api import parse, supported_extensions
from .harness import AI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="terbium",
        description="Algorithmic multi-file parser (PDF/PPTX/XLSX/CSV) that knows when it is stuck.",
    )
    ap.add_argument("file", help="path to a " + "/".join(supported_extensions()) + " file")
    ap.add_argument("--schema", default="generic", help="generic (default) or furniture")
    ap.add_argument("--json", metavar="OUT", help="write records as JSON to this path (or - for stdout)")
    ap.add_argument("--ai", action="store_true", help="enable the AI lane using env keys")
    ap.add_argument("--tier", choices=["haiku", "sonnet", "opus"], help="pin the AI model tier")
    ap.add_argument("--limit", type=int, default=12, help="how many records to preview")
    ap.add_argument("--version", action="version", version=f"terbium {__version__}")
    args = ap.parse_args(argv)

    ai = AI(force_tier=args.tier) if args.ai else None
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

    print(f"terbium {__version__}  ·  {doc.source_kind}  ·  {len(doc.pages)} pages")
    print(f"records: {doc.stats.total}  (confident {doc.stats.confident}, ambiguous {doc.stats.ambiguous})")
    if doc.used_ai:
        print("AI lane: engaged on hard tables")
    print("-" * 60)
    for r in doc.records[: args.limit]:
        flag = "" if r.confidence >= doc.stats.threshold else "  [ambiguous]"
        print(f"{r.sku or '-':>8}  {r.confidence:.2f}  {r.fields}{flag}")
    if doc.stats.total > args.limit:
        print(f"... and {doc.stats.total - args.limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
