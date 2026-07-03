"""Route a hard page to the cheapest model that can actually handle it.

The whole reason terbium is cost-sane: AI is only invoked on tables the engine
could not resolve, and even then the tier scales with how hard the table is.
"""
from __future__ import annotations

from ..model.table import ExtractedTable

HAIKU, SONNET, OPUS = "haiku", "sonnet", "opus"

# Concrete model ids per tier (current Claude family).
MODEL_IDS = {
    HAIKU: "claude-haiku-4-5",
    SONNET: "claude-sonnet-5",
    OPUS: "claude-opus-4-8",
}


def complexity(table: ExtractedTable) -> float:
    """A rough 0..1 difficulty score for a table."""
    size = table.n_rows * max(1, table.n_cols)
    size_term = min(1.0, size / 24.0)
    col_term = min(1.0, table.n_cols / 6.0)
    unconf = 1.0 - table.confidence
    return round(min(1.0, 0.5 * unconf + 0.3 * size_term + 0.2 * col_term), 3)


def pick_tier(table: ExtractedTable, force: str = None) -> str:
    if force in (HAIKU, SONNET, OPUS):
        return force
    c = complexity(table)
    if table.confidence < 0.4 or c >= 0.6:
        return OPUS
    if c >= 0.3:
        return SONNET
    return HAIKU


def recommend_tier(tables) -> str:
    """The single tier to suggest in an escalation message for a set of tables."""
    if any(t.confidence < 0.4 for t in tables):
        return OPUS
    if any(complexity(t) >= 0.3 for t in tables):
        return SONNET
    return HAIKU
