"""Resume schema: candidate header + sectioned records.

Header (name, email, phone, location, links) plus flat CSV rows for experience,
education, skills, projects, certifications with a section field.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..layout import signals
from ..layout.lines import cluster_lines
from ..model.elements import Page
from ..model.record import Record
from ..model.table import ExtractedTable
from .base import Schema, register_schema

SECTION_SYNONYMS = [
    ("experience", ["experience", "work history", "employment", "professional experience"]),
    ("education", ["education", "academic", "qualifications"]),
    ("skills", ["skills", "technical skills", "core competencies", "expertise"]),
    ("projects", ["projects", "portfolio"]),
    ("certifications", ["certifications", "certificates", "licenses"]),
]

_SECTION_RE = re.compile(
    r"^(experience|education|skills|projects|certifications|summary|objective)\s*:?\s*$",
    re.IGNORECASE,
)


def _map_section(text: str) -> Optional[str]:
    t = text.strip().lower().rstrip(":")
    for canon, subs in SECTION_SYNONYMS:
        for s in subs:
            if s in t or t == s:
                return canon
    m = _SECTION_RE.match(text.strip())
    if m:
        return m.group(1).lower()
    return None


def _extract_header(page: Page) -> Dict[str, str]:
    lines = cluster_lines(page.words)
    if not lines:
        return {}
    header: Dict[str, str] = {}
    text = "\n".join(ln.text for ln in lines)
    emails = signals.find_emails(text)
    phones = signals.find_phones(text)
    urls = signals.find_urls(text)
    if emails:
        header["email"] = emails[0]
    if phones:
        header["phone"] = phones[0]
    if urls:
        header["links"] = ", ".join(urls[:3])
    # name: largest short line near top
    top_lines = sorted(lines, key=lambda l: l.y)[:8]
    med = page.median_size or 12.0
    candidates = [ln for ln in top_lines if ln.max_size >= med * 1.1 and len(ln.text.split()) <= 5]
    if candidates:
        header["name"] = max(candidates, key=lambda l: l.max_size).text.strip()
    elif top_lines:
        header["name"] = top_lines[0].text.strip()
    return header


def _parse_sections(pages: List[Page]) -> List[Record]:
    records: List[Record] = []
    header = _extract_header(pages[0]) if pages else {}
    if header:
        h = dict(header)
        h["section"] = "header"
        records.append(
            Record(sku=None, fields=h, source_page=0, confidence=0.8,
                   reasons=["resume header"])
        )
    current_section: Optional[str] = None
    for page in pages:
        lines = cluster_lines(page.words)
        for ln in lines:
            sec = _map_section(ln.text)
            if sec:
                current_section = sec
                continue
            if not current_section or not ln.text.strip():
                continue
            fields = dict(header)
            fields["section"] = current_section
            fields["content"] = ln.text.strip()
            records.append(
                Record(sku=None, fields=fields, source_page=page.index,
                       confidence=0.7, reasons=[f"resume {current_section} entry"])
            )
    return records


@register_schema
class ResumeSchema(Schema):
    name = "resume"

    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        records: List[Record] = []
        for t in tables:
            headers = t.col_headers
            for row in t.cells:
                fields: Dict[str, str] = {"section": "table"}
                for ci, cell in enumerate(row):
                    if cell is None or cell == "":
                        continue
                    hdr = headers[ci] if ci < len(headers) else f"col{ci + 1}"
                    fields[hdr.lower().replace(" ", "_")] = str(cell)
                records.append(
                    Record(sku=None, fields=fields, source_page=t.source_page,
                           confidence=t.confidence, reasons=list(t.reasons))
                )
        return records

    def build_from_pages(self, pages: List[Page]) -> List[Record]:
        return _parse_sections(pages)
