"""AI configuration. Entirely opt-in - terbium runs fully without it."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AI:
    """Credentials + policy for the optional AI lane.

    Keys fall back to the environment, so ``terbium.parse(path, ai=terbium.AI())``
    picks up ANTHROPIC_API_KEY / GEMINI_API_KEY automatically.
    """
    anthropic_key: Optional[str] = None
    gemini_key: Optional[str] = None
    force_tier: Optional[str] = None       # "haiku" | "sonnet" | "opus" | None (auto)
    enable_vision: bool = True

    def __post_init__(self):
        self.anthropic_key = self.anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
        self.gemini_key = self.gemini_key or os.environ.get("GEMINI_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self.anthropic_key or self.gemini_key)

    @property
    def has_vision(self) -> bool:
        return self.enable_vision and self.available


def resolve(ai) -> Optional[AI]:
    """Accept True / an AI / None and normalize to an AI or None."""
    if ai is None or ai is False:
        return None
    if ai is True:
        ai = AI()
    return ai if ai.available else None
