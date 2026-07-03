"""Parse a furniture catalogue PDF and show what terbium recovers.

Usage:
    python examples/furniture_catalogue.py "/path/to/Furniture Catalogue.pdf"

With no AI key this runs the algorithmic engine only and prints an escalation
message for any pages it could not resolve. Add ANTHROPIC_API_KEY to let it
route the hard pages to a model.
"""
import sys

import terbium


def main(path: str) -> int:
    doc = terbium.parse(path, schema="furniture", ai=terbium.AI())  # AI used only if a key exists
    print(f"source     : {doc.source_kind}, {len(doc.pages)} pages")
    print(f"records    : {doc.stats.total}")
    print(f"confident  : {doc.stats.confident}")
    print(f"ambiguous  : {doc.stats.ambiguous}")
    print(f"used AI     : {doc.used_ai}")
    print("-" * 64)

    # show the first handful of confident products
    for r in doc.confident_records[:10]:
        print(
            f"{r.sku:>7}  {r.get('product', '?'):<26.26}  "
            f"{str(r.get('size', '')):<20.20}  {r.get('finish', '')}"
        )

    if doc.escalation:
        print("-" * 64)
        print(doc.escalation)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
