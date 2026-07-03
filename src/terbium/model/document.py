"""The top-level result object returned by ``terbium.parse``."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

from .elements import Page
from .record import Record


@dataclass
class Stats:
    total: int = 0
    confident: int = 0
    ambiguous: int = 0
    threshold: float = 0.72

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "confident": self.confident,
            "ambiguous": self.ambiguous,
        }

    def __repr__(self) -> str:
        return (
            f"Stats(total={self.total}, confident={self.confident}, "
            f"ambiguous={self.ambiguous})"
        )


@dataclass
class ParsedDocument:
    path: str
    source_kind: str
    pages: List[Page] = field(default_factory=list)
    records: List[Record] = field(default_factory=list)
    stats: Stats = field(default_factory=Stats)
    escalation: Optional[str] = None     # human-readable "bring an AI key" message
    used_ai: bool = False

    @property
    def ambiguous_records(self) -> List[Record]:
        return [r for r in self.records if r.confidence < self.stats.threshold]

    @property
    def confident_records(self) -> List[Record]:
        return [r for r in self.records if r.confidence >= self.stats.threshold]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "source_kind": self.source_kind,
            "stats": self.stats.to_dict(),
            "used_ai": self.used_ai,
            "escalation": self.escalation,
            "records": [r.to_dict() for r in self.records],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:
        tail = " +escalation" if self.escalation else ""
        return (
            f"ParsedDocument({self.source_kind}, {len(self.pages)} pages, "
            f"{len(self.records)} records, {self.stats!r}{tail})"
        )
