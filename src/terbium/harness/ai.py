"""AI configuration. Entirely opt-in - terbium runs fully without it."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AI:
    """Credentials + policy for the optional AI lane.

    Keys fall back to the environment, so ``terbium.parse(path, ai=terbium.AI())``
    picks up provider keys automatically. Claude (Anthropic) is preferred when
    multiple keys are set unless ``provider`` pins one.
    """
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None
    kimi_key: Optional[str] = None
    grok_key: Optional[str] = None
    gemini_key: Optional[str] = None
    provider: Optional[str] = None       # "anthropic"|"openai"|"kimi"|"grok"|"gemini"
    force_tier: Optional[str] = None     # "haiku" | "sonnet" | "opus" | None (auto)
    enable_vision: bool = True

    def __post_init__(self):
        self.anthropic_key = self.anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = self.openai_key or os.environ.get("OPENAI_API_KEY")
        self.kimi_key = self.kimi_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        self.grok_key = self.grok_key or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        self.gemini_key = self.gemini_key or os.environ.get("GEMINI_API_KEY")

    @property
    def available(self) -> bool:
        return bool(
            self.anthropic_key
            or self.openai_key
            or self.kimi_key
            or self.grok_key
            or self.gemini_key
        )

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
