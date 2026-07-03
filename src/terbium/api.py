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
from .layout import confidence as _confidence
from .layout import dehead, grid
from .layout.columns import split_columns
from .layout.lines import cluster_lines
from .model.document import ParsedDocument, Stats
from .model.elements import Page
from .model.table import ExtractedTable
from .schema import get_schema
from .harness import arrange_tables, build_message, resolve

DEFAULT_THRESHOLD = 0.72


def _assemble_tables(pages: List[Page]) -> List[ExtractedTable]:
    tables: List[ExtractedTable] = []
    pdf_pages = [p for p in pages if p.source_kind == "pdf" and p.words]
    stripper = dehead.build_stripper(pdf_pages) if pdf_pages else None
    for p in pages:
        if p.native_tables:
            tables.extend(p.native_tables)
        elif p.source_kind == "pdf" and p.words:
            for word_group in split_columns(p):
                lines = cluster_lines(word_group)
                if stripper:
                    lines = [ln for ln in lines if not stripper(ln, p)]
                tables.extend(grid.extract_tables(lines, p))
    return tables


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

    tables = _assemble_tables(pages)
    for t in tables:
        _confidence.score_table(t)

    ai_cfg = resolve(ai)
    hard = [t for t in tables if t.confidence < threshold]
    used_ai = False
    if hard and ai_cfg is not None:
        fixed = arrange_tables(path, pages, hard, ai_cfg)
        used_ai = fixed > 0
        hard = [t for t in tables if t.confidence < threshold]

    schema_obj = get_schema(schema)
    records = []
    for t in tables:
        recs = schema_obj.build_records([t])
        if t.origin == "ai":
            for r in recs:
                r.origin = "ai"
        records.extend(recs)

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

    if hard:
        doc.escalation = build_message(records, hard, threshold)
        if announce and ai_cfg is None:
            print(doc.escalation, file=sys.stderr)

    return doc


__all__ = ["parse", "supported_extensions", "DEFAULT_THRESHOLD"]
