"""``terbium.parse`` - the one function most users call.

Flow: adapt -> classify -> assemble tables (native, or reconstructed from PDF
geometry) -> score confidence -> (optionally) send only the hard tables to AI ->
build typed records -> if anything is still shaky and no key was given, attach and
announce an escalation message.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from .classify import classify, schema_for_type
from .documents import get_adapter, supported_extensions
from .layout import confidence as _confidence
from .layout import dehead, grid
from .layout.columns import split_columns
from .layout.labels import extract_labels, page_is_lookbook
from .layout.lines import cluster_lines
from .layout.tables import detect_tables, is_data_table
from .model.document import ParsedDocument, Stats
from .model.elements import Page
from .model.record import Record
from .model.table import ExtractedTable
from .schema import get_schema
from .harness import arrange_tables, build_message, resolve

DEFAULT_THRESHOLD = 0.72


def _assemble_tables(pages: List[Page], furniture_mode: bool = False) -> Tuple[List[ExtractedTable], List[int]]:
    """Return (tables, image_only_page_indices).

    By default a content-agnostic geometric detector reconstructs any column
    aligned table. ``furniture_mode`` swaps in the specialized cross-tab detector.
    If a page yields no table, label-grid extraction runs on the full page. A page
    with images but almost no text and no table is recorded as image-only.
    """
    detector = grid.extract_tables if furniture_mode else detect_tables
    tables: List[ExtractedTable] = []
    image_only: List[int] = []
    pdf_pages = [p for p in pages if p.source_kind == "pdf"]
    text_pdf = [p for p in pdf_pages if p.words]
    stripper = dehead.build_stripper(text_pdf) if text_pdf else None

    # Pass 1: native tables + reconstructed tables.
    matrix_pages = set()
    for p in pages:
        if p.native_tables:
            tables.extend(p.native_tables)
            continue
        if p.source_kind != "pdf" or not p.words:
            continue
        matrix: List[ExtractedTable] = []
        for word_group in split_columns(p):
            lines = cluster_lines(word_group)
            if stripper:
                lines = [ln for ln in lines if not stripper(ln, p)]
            found = detector(lines, p)
            if not furniture_mode and len(p.images) >= 3:
                # on an image-heavy page, a text-only "table" is a lookbook grid
                found = [t for t in found if is_data_table(t)]
            matrix.extend(found)
        if matrix:
            tables.extend(matrix)
            matrix_pages.add(p.index)

    # Pass 2: label grids (per-page lookbook) + image-only detection.
    for p in pdf_pages:
        if p.native_tables or p.index in matrix_pages:
            continue
        produced = False
        if page_is_lookbook(p, matrix_pages) and p.words:
            full = cluster_lines(p.words)
            if stripper:
                full = [ln for ln in full if not stripper(ln, p)]
            lab = extract_labels(full, p)
            if lab:
                tables.append(lab)
                produced = True
        if p.images and len(p.words) < 5 and not produced:
            image_only.append(p.index)
    return tables, image_only


def parse(
    path: str,
    schema=None,
    ai=None,
    threshold: float = DEFAULT_THRESHOLD,
    announce: bool = True,
    ocr="auto",
    doc_type: str = "auto",
) -> ParsedDocument:
    """Parse a PDF/PPTX/XLSX/CSV/image file into structured, confidence-scored records.

    ``schema``: "generic" (default) or "furniture"/"product"/"transaction"/"resume",
    or a Schema instance.
    ``doc_type``: ``"auto"`` classifies after adapt, or override with
    catalog/transaction/resume/table/deck/lookbook.
    ``ai``: a ``terbium.AI(...)``, ``True`` (use env keys), or ``None`` (off).
    ``threshold``: confidence below which a record is "ambiguous".
    ``ocr``: ``"auto"`` reads image-only pages with a local Tesseract pass (no
    API key; no-op when Tesseract is absent). ``True``/``False`` forces it.
    ``announce``: print the escalation message to stderr when AI could help but
    no key is set. This is terbium telling you it is stuck.
    """
    adapter = get_adapter(path)
    pages = adapter.parse(path)
    source_kind = pages[0].source_kind if pages else "unknown"
    if source_kind in ("pdf", "image") and pages:
        from .layout import ocr as _ocr
        use_ocr = ocr if isinstance(ocr, bool) else (ocr == "auto" and _ocr.available())
        if use_ocr:
            if source_kind == "pdf":
                _ocr.enrich_pdf_pages(pages, path)
            elif source_kind == "image" and not pages[0].words:
                pages[0].words = _ocr.ocr_image_words(open(path, "rb").read())

    classified_type = doc_type
    class_scores = {}
    if doc_type == "auto":
        classified_type, class_scores = classify(pages)
    elif doc_type == "catalog":
        classified_type = "catalog"

    if schema is None:
        if doc_type == "auto":
            schema = schema_for_type(classified_type)
        elif doc_type in ("catalog", "lookbook", "table"):
            schema = "product"
        elif doc_type == "transaction":
            schema = "transaction"
        elif doc_type == "resume":
            schema = "resume"
    schema_obj = get_schema(schema)
    furniture_mode = getattr(schema_obj, "name", None) == "furniture"
    tables, image_only = _assemble_tables(pages, furniture_mode)
    matrix_tables = [t for t in tables if t.kind != "labels"]
    label_tables = [t for t in tables if t.kind == "labels"]
    for t in matrix_tables:
        _confidence.score_table(t)

    ai_cfg = resolve(ai)
    hard = [t for t in matrix_tables if t.confidence < threshold]
    used_ai = False
    if hard and ai_cfg is not None:
        fixed = arrange_tables(path, pages, hard, ai_cfg)
        used_ai = fixed > 0
        hard = [t for t in matrix_tables if t.confidence < threshold]

    records = []
    for t in matrix_tables:
        recs = schema_obj.build_records([t])
        if t.origin == "ai":
            for r in recs:
                r.origin = "ai"
        records.extend(recs)
    for t in label_tables:
        for row in t.cells:
            fields = {"name": row[0]}
            if t.title:
                fields["collection"] = t.title
            records.append(
                Record(sku=None, fields=fields, source_page=t.source_page,
                       confidence=t.confidence, reasons=list(t.reasons))
            )

    # transaction/resume page-based extraction when tables yielded little
    if classified_type == "transaction" and len(records) < 2:
        from .schema.transaction import TransactionSchema
        if isinstance(schema_obj, TransactionSchema):
            page_recs = schema_obj.build_from_pages(pages)
            if page_recs:
                records = page_recs
    if classified_type == "resume" and len(records) < 2:
        from .schema.resume import ResumeSchema
        if isinstance(schema_obj, ResumeSchema):
            page_recs = schema_obj.build_from_pages(pages)
            if page_recs:
                records = page_recs

    if classified_type == "transaction" and ai_cfg is not None and records:
        from .harness.transaction_ai import enrich_transactions
        from .layout.lines import cluster_lines as _cl
        page_text = "\n".join(
            ln.text for p in pages for ln in _cl(p.words) if ln.text.strip()
        )
        records = enrich_transactions(records, page_text, ai_cfg)
        used_ai = True

    stats = Stats(
        total=len(records),
        confident=sum(1 for r in records if r.confidence >= threshold),
        ambiguous=sum(1 for r in records if r.confidence < threshold),
        threshold=threshold,
    )
    doc = ParsedDocument(
        path=path,
        source_kind=source_kind,
        pages=pages,
        records=records,
        stats=stats,
        used_ai=used_ai,
        doc_type=classified_type,
        class_scores=class_scores,
    )

    notes = []
    if hard:
        notes.append(build_message(records, hard, threshold))
    if image_only and ai_cfg is None:
        pgs = ", ".join(str(i + 1) for i in image_only[:10])
        more = ", ..." if len(image_only) > 10 else ""
        notes.append(
            f"terbium: {len(image_only)} page(s) are image-only with no text layer "
            f"(e.g. {pgs}{more}). Read them with the vision lane: pass "
            f"ai=terbium.AI(...) with a key."
        )
    if notes:
        doc.escalation = "\n".join(notes)
        if announce and ai_cfg is None:
            print(doc.escalation, file=sys.stderr)

    return doc


__all__ = ["parse", "supported_extensions", "DEFAULT_THRESHOLD"]
