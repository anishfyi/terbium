# Schemas

A schema is the one place that knows what a row of output should look like.
Everything upstream is domain-agnostic; swap the schema and keep the engine.

## Built-in schemas

### generic (default)

- **grid** tables (XLSX / CSV / PPTX): one record per body row, columns become
  fields. A compact, digit-bearing row key is recognized as the `sku`.
- **matrix** tables (a PDF finish x size grid): one record per filled cell, with
  `row`, `column`, and `title` fields.

```python
doc = terbium.parse("stock.xlsx")            # schema defaults to "generic"
doc.records[0].fields
# {"row_label": "35155", "Product": "Sequence table", "Qty": "12", "title": "Stock"}
```

### furniture

One record per article number, tuned for a catalogue matrix:

```python
doc = terbium.parse("catalogue.pdf", schema="furniture")
doc.records[0].fields
# {"product": "Barrow pouf", "size": "40 × 40 × 40 cm", "finish": "off white",
#  "dimensions_cm": "40 x 40 x 40 cm", "dimensions_in": '15.5" x 15.5" x 15.5"'}
```

## Writing your own

```python
from terbium.schema import Schema, register_schema
from terbium.model.record import Record

@register_schema
class PricelistSchema(Schema):
    name = "pricelist"

    def build_records(self, tables):
        records = []
        for t in tables:
            for rh, ch, val in t.iter_cells():
                records.append(Record(
                    sku=val, fields={"item": t.title, "variant": ch},
                    source_page=t.source_page, confidence=t.confidence,
                    reasons=list(t.reasons),
                ))
        return records
```

Then `terbium.parse(path, schema="pricelist")`.
