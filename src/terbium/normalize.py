"""Deterministic normalization: make product fields feed-ready without a model.

Dimensions collapse to millimetres, colours and materials fold into small
controlled families. All additive: raw values are kept, normalized keys are added
alongside (color_family, material_family, dimensions_mm). The vocabularies start
deliberately small and grow from the evaluation set, per the roadmap.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .layout import signals

_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0}

# colour term -> family. Longest term wins, so "off white" beats "white".
COLOR_FAMILIES: Dict[str, List[str]] = {
    "white": ["off white", "off-white", "ivory", "cream", "ecru", "chalk", "snow", "white"],
    "black": ["jet black", "black", "onyx", "ebony", "jet"],
    "grey": ["charcoal", "graphite", "slate", "silver", "dove", "ash grey", "grey", "gray"],
    "brown": ["chocolate", "walnut", "coffee", "mocha", "caramel", "biscuit", "taupe",
              "camel", "beige", "sand", "tan", "brown"],
    "red": ["burgundy", "crimson", "scarlet", "terracotta", "maroon", "wine", "rust", "red"],
    "orange": ["tangerine", "apricot", "ginger", "amber", "copper", "orange"],
    "yellow": ["mustard", "ochre", "honey", "gold", "yellow"],
    "green": ["olive", "sage", "emerald", "forest", "khaki", "moss", "mint", "green"],
    "blue": ["navy", "teal", "indigo", "cobalt", "denim", "petrol", "azure", "blue"],
    "purple": ["aubergine", "lavender", "violet", "lilac", "plum", "mauve", "purple"],
    "pink": ["blush", "fuchsia", "magenta", "coral", "rose", "pink"],
    "multi": ["multicolour", "multicolor", "assorted", "multi"],
}

# material term -> family.
MATERIAL_FAMILIES: Dict[str, List[str]] = {
    "wood": ["rubberwood", "plywood", "veneer", "walnut", "acacia", "mango", "teak",
             "birch", "oak", "pine", "ash", "mdf", "wood"],
    "metal": ["aluminium", "aluminum", "stainless steel", "steel", "brass", "copper",
              "chrome", "bronze", "iron", "zinc", "metal"],
    "leather": ["full-grain leather", "leather", "suede", "nubuck", "hide"],
    "textile": ["polypropylene", "polyacrylic", "polyester", "viscose", "acrylic",
                "chenille", "velvet", "canvas", "cotton", "linen", "wool", "jute",
                "sisal", "nylon", "felt", "fabric", "fibre", "fiber"],
    "glass": ["crystal", "glass"],
    "stone": ["marble", "granite", "terrazzo", "porcelain", "ceramic", "concrete",
              "slate", "stone"],
    "rattan": ["water hyacinth", "seagrass", "bamboo", "rattan", "wicker", "cane"],
    "plastic": ["polycarbonate", "resin", "plastic", "pvc"],
}


def _classify(value: str, families: Dict[str, List[str]]) -> Optional[str]:
    v = (value or "").lower()
    if not v:
        return None
    best_family, best_len = None, 0
    for family, terms in families.items():
        for term in terms:
            if term in v and len(term) > best_len:
                best_family, best_len = family, len(term)
    return best_family


def color_family(value: str) -> Optional[str]:
    return _classify(value, COLOR_FAMILIES)


def material_family(value: str) -> Optional[str]:
    return _classify(value, MATERIAL_FAMILIES)


def dimensions_mm(value: str) -> Optional[dict]:
    """Parse a dimension string to millimetres, keeping the raw form."""
    dims = signals.find_dimensions(value or "")
    if not dims:
        return None
    d = dims[0]
    factor = _TO_MM.get(d["unit"], 1.0)
    return {"values_mm": [round(v * factor, 1) for v in d["values"]],
            "unit": d["unit"], "raw": d["raw"]}


def enrich_fields(fields: dict) -> dict:
    """Add normalized keys to a product's fields in place, and return it."""
    if fields.get("color"):
        fam = color_family(fields["color"])
        if fam:
            fields["color_family"] = fam
    if fields.get("material"):
        fam = material_family(fields["material"])
        if fam:
            fields["material_family"] = fam
    if fields.get("dimensions"):
        mm = dimensions_mm(fields["dimensions"])
        if mm:
            fields["dimensions_mm"] = mm["values_mm"]
    return fields
