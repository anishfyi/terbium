"""Schemas map reconstructed tables to typed records.

A schema is the one place that knows what a row of output should look like.
Everything upstream is domain-agnostic; swap the schema, keep the engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..model.record import Record
from ..model.table import ExtractedTable


class Schema(ABC):
    name: str = "base"

    @abstractmethod
    def build_records(self, tables: List[ExtractedTable]) -> List[Record]:
        ...


_SCHEMAS: dict = {}


def register_schema(cls):
    _SCHEMAS[cls.name] = cls()
    return cls


def get_schema(name) -> Schema:
    if isinstance(name, Schema):
        return name
    if name is None:
        name = "generic"
    if name not in _SCHEMAS:
        raise ValueError(
            f"unknown schema '{name}'. Available: " + ", ".join(sorted(_SCHEMAS)) + "."
        )
    return _SCHEMAS[name]
