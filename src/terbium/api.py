"""``terbium.parse`` - the one function most users call.

Flow: adapt -> assemble tables (native, or reconstructed from PDF geometry) ->
score confidence -> (optionally) send only the hard tables to AI -> build typed
records -> if anything is still shaky and no key was given, attach and announce
an escalation message.
"""
from __future__ import annotations

import sys
from typing import List, Optional

from .documents import get_adapter, supported_extensions
from typing import List, Tuple

from .layout import confidence as _confidence
from .layout import dehead, grid
from .layout.columns import split_columns
from .layout.labels import extract_labels
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

    # A document that is mostly matrices is a catalogue; one that is mostly not
    # is a lookbook. Only lookbooks get label extraction, so a structured parse
    # is never polluted by stray names.
    lookbook = pdf_pages and (len(matrix_pages) / len(pdf_pages)) < 0.2

    # Pass 2: label grids (lookbook only) + image-only detection.
    for p in pdf_pages:
        if p.native_tables or p.index in matrix_pages:
            continue
        produced = False
        if lookbook and p.words:
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
) -> ParsedDocument:
    """Parse a PDF/PPTX/XLSX/CSV file into structured, confidence-scored records.

    ``schema``: "generic" (default) or "furniture", or a Schema instance.
    ``ai``: a ``terbium.AI(...)``, ``True`` (use env keys), or ``None`` (off).
    ``threshold``: confidence below which a record is "ambiguous".
    ``announce``: print the escalation message to stderr when AI could help but
    no key is set. This is terbium telling you it is stuck.
    """
    adapter = get_adapter(path)
    pages = adapter.parse(path)
    source_kind = pages[0].source_kind if pages else "unknown"

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
