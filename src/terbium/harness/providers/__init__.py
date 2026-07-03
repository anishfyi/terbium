"""Provider selection. Anthropic is preferred for the text arrange step; Gemini
is used when only a Gemini key is present, and for vision."""
from __future__ import annotations

from typing import Optional

from ..ai import AI
from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider

__all__ = ["LLMProvider", "AnthropicProvider", "GeminiProvider", "text_provider", "vision_provider"]


def text_provider(ai: AI) -> Optional[LLMProvider]:
    if ai.anthropic_key:
        return AnthropicProvider(ai.anthropic_key)
    if ai.gemini_key:
        return GeminiProvider(ai.gemini_key)
    return None


def vision_provider(ai: AI) -> Optional[LLMProvider]:
    # Both families are vision-capable; prefer whichever key is present.
    if ai.anthropic_key:
        return AnthropicProvider(ai.anthropic_key)
    if ai.gemini_key:
        return GeminiProvider(ai.gemini_key)
    return None
