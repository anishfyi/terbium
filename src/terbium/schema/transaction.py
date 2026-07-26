"""Transaction schema: invoice, bill, receipt, PO, quote via FIELD_SYNONYMS.

Header fields (number, date, due date, vendor, customer, tax id, payment method),
line-item records (description, qty, unit price, amount), and totals (subtotal,
tax, total).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..layout import forms, signals
from ..layout.lines import cluster_lines
from ..model.elements import Page
from ..model.record import Record
from ..model.table import ExtractedTable
from .base import Schema, register_schema

FIELD_SYNONYMS = [
    ("number", ["invoice number", "invoice no", "inv no", "receipt no", "bill no",
                "po number", "purchase order", "quote no", "reference", "ref"]),
    ("date", ["invoice date", "bill date", "date issued", "date"]),
    ("due_date", ["due date", "payment due", "pay by"]),
    ("vendor", ["vendor", "supplier", "from", "seller", "merchant"]),
    ("customer", ["customer", "bill to", "sold to", "ship to", "client"]),
    ("tax_id", ["tax id", "vat", "gst", "ein", "abn"]),
    ("payment_method", ["payment method", "paid by", "payment type"]),
    ("description", ["description", "item", "product", "details", "service"]),
    ("quantity", ["qty", "quantity", "units"]),
    ("unit_price", ["unit price", "rate", "price each", "unit cost"]),
    ("amount", ["amount", "line total", "extended", "total"]),
    ("subtotal", ["subtotal", "sub total", "net amount"]),
    ("tax", ["tax", "vat amount", "gst amount", "sales tax"]),
    ("total", ["total due", "amount due", "grand total", "total", "balance due"]),
]


def _map_header(header: str) -> Optional[str]:
    h = (header or "").strip().lower()
    if not h:
        return None
    best, best_len = None, 0
    for canonical, subs in FIELD_SYNONYMS:
        for s in subs:
            if s in h and len(s) > best_len:
                best, best_len = canonical, len(s)
    return best


def _header_from_pages(pages: List[Page]) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for page in pages:
        for pair in forms.extract_kv_pairs(page):
            canon = _map_header(pair["label"])
            if canon and canon not in fields:
                fields[canon] = pair["value"]
        text = "\n".join(ln.text for ln in cluster_lines(page.words))
        for inv in signals.find_invoice_numbers(text):
            fields.setdefault("number", inv)
        for tid in signals.find_tax_ids(text):
            fields.setdefault("tax_id", tid)
        dates = signals.find_dates(text)
        if dates and "date" not in fields:
            fields["date"] = dates[0]
    return fields


@register_schema
class TransactionSchema(Schema):
    name = "transaction"

    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        records: List[Record] = []
        header: Dict[str, str] = {}
        pages_by_idx: Dict[int, Page] = {}

        for t in tables:
            headers = t.col_headers
            for row in t.cells:
                fields = dict(header)
                line_fields: Dict[str, str] = {}
                for ci, cell in enumerate(row):
                    if cell is None or cell == "":
                        continue
                    hdr = headers[ci] if ci < len(headers) else f"col{ci + 1}"
                    canon = _map_header(hdr)
                    if canon in ("subtotal", "tax", "total", "number", "date",
                                   "due_date", "vendor", "customer", "tax_id",
                                   "payment_method"):
                        header.setdefault(canon, str(cell))
                        fields[canon] = str(cell)
                    elif canon:
                        line_fields[canon] = str(cell)
                    else:
                        line_fields[hdr] = str(cell)
                fields.update(line_fields)
                fields["record_type"] = "line_item" if line_fields.get("description") or line_fields.get("amount") else "header"
                if fields.get("record_type") == "line_item" or len(line_fields) >= 2:
                    records.append(
                        Record(sku=fields.get("number"), fields=fields,
                               source_page=t.source_page, confidence=t.confidence,
                               reasons=list(t.reasons))
                    )

        if not records:
            # fall back to key-value pairs only
            for t in tables:
                page = pages_by_idx.get(t.source_page)
                if page:
                    hdr = _header_from_pages([page])
                    for k, v in hdr.items():
                        rec = dict(hdr)
                        rec["record_type"] = "header"
                        records.append(
                            Record(sku=hdr.get("number"), fields=rec,
                                   source_page=t.source_page, confidence=0.7,
                                   reasons=["key-value header fields"])
                        )
                        break
        return records

    def build_from_pages(self, pages: List[Page]) -> List[Record]:
        """Build transaction records from pages (KV + amount rows)."""
        header = _header_from_pages(pages)
        records: List[Record] = []
        if header:
            h = dict(header)
            h["record_type"] = "header"
            records.append(
                Record(sku=header.get("number"), fields=h, source_page=0,
                       confidence=0.75, reasons=["transaction header from key-value pairs"])
            )
        for page in pages:
            for pair in forms.extract_kv_pairs(page):
                canon = _map_header(pair["label"])
                if canon in ("subtotal", "tax", "total"):
                    fields = dict(header)
                    fields[canon] = pair["value"]
                    fields["record_type"] = "total"
                    records.append(
                        Record(sku=header.get("number"), fields=fields,
                               source_page=page.index, confidence=0.7,
                               reasons=["total field"])
                    )
                elif pair["kind"] == "amount_row":
                    fields = dict(header)
                    fields["description"] = pair["label"]
                    fields["amount"] = pair["value"]
                    fields["record_type"] = "line_item"
                    records.append(
                        Record(sku=header.get("number"), fields=fields,
                               source_page=page.index, confidence=0.65,
                               reasons=["amount row"])
                    )
        return records
