"""Adapter interface + registry. One adapter per file format.

Adapters do exactly one job: turn bytes on disk into normalized ``Page`` objects
(words with positions, images, and - when the format exposes it natively - ready
made tables). Everything smart happens after, on that uniform representation.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List

from ..model.elements import Page


class DocumentAdapter(ABC):
    extensions: tuple = ()

    @abstractmethod
    def parse(self, path: str) -> List[Page]:
        ...


_REGISTRY: dict = {}


def register(adapter_cls):
    """Class decorator: instantiate the adapter and index it by extension."""
    instance = adapter_cls()
    for ext in adapter_cls.extensions:
        _REGISTRY[ext.lower()] = instance
    return adapter_cls


def get_adapter(path: str) -> DocumentAdapter:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in _REGISTRY:
        raise ValueError(
            f"terbium has no adapter for '.{ext}'. Supported: "
            + ", ".join(sorted(_REGISTRY)) + "."
        )
    return _REGISTRY[ext]


def supported_extensions() -> List[str]:
    return sorted(_REGISTRY)
