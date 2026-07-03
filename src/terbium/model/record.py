"""The unit of output: one arranged record with a confidence it stands behind."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Record:
    """One arranged row of data.

    ``fields`` holds the schema-specific payload (e.g. product, size, finish,
    dimensions_cm). Common keys are also reachable as attributes, so
    ``record.finish`` works as well as ``record.fields["finish"]``.
    """
    sku: Optional[str]
    fields: dict
    source_page: int
    confidence: float
    reasons: List[str] = field(default_factory=list)
    origin: str = "algorithmic"          # algorithmic | ai

    def __getattr__(self, name: str) -> Any:
        # Only reached when normal attribute lookup fails, so this never
        # shadows the real dataclass fields above.
        if name.startswith("_") or name == "fields":
            raise AttributeError(name)
        fields = self.__dict__.get("fields", {})
        if name in fields:
            return fields[name]
        raise AttributeError(name)

    def get(self, name: str, default: Any = None) -> Any:
        return self.fields.get(name, default)

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            **self.fields,
            "source_page": self.source_page,
            "confidence": round(self.confidence, 3),
            "origin": self.origin,
        }
