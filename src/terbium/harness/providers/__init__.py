"""Provider selection. Anthropic (Claude) is preferred; GPT, Kimi, Grok, and
Gemini are used when that is the key present or when ``AI(provider=...)`` pins one."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..ai import AI
from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .grok_provider import GrokProvider
from .kimi_provider import KimiProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "KimiProvider",
    "GrokProvider",
    "text_provider",
    "vision_provider",
    "provider_name",
]

_DEFAULT_ORDER = ("anthropic", "openai", "kimi", "grok", "gemini")


def _factories(ai: AI) -> Dict[str, Callable[[], Optional[LLMProvider]]]:
    return {
        "anthropic": lambda: AnthropicProvider(ai.anthropic_key) if ai.anthropic_key else None,
        "openai": lambda: OpenAIProvider(ai.openai_key) if ai.openai_key else None,
        "kimi": lambda: KimiProvider(ai.kimi_key) if ai.kimi_key else None,
        "grok": lambda: GrokProvider(ai.grok_key) if ai.grok_key else None,
        "gemini": lambda: GeminiProvider(ai.gemini_key) if ai.gemini_key else None,
    }


def _pick(ai: AI, order: List[str]) -> Optional[LLMProvider]:
    factories = _factories(ai)
    for name in order:
        provider = factories.get(name, lambda: None)()
        if provider is not None:
            return provider
    return None


def _order(ai: AI) -> List[str]:
    if ai.provider:
        return [ai.provider]
    return list(_DEFAULT_ORDER)


def text_provider(ai: AI) -> Optional[LLMProvider]:
    return _pick(ai, _order(ai))


def vision_provider(ai: AI) -> Optional[LLMProvider]:
    # Vision-capable across all lanes; same preference order as text.
    return _pick(ai, _order(ai))


def provider_name(ai: AI) -> Optional[str]:
    order = _order(ai)
    factories = _factories(ai)
    for name in order:
        if factories.get(name, lambda: None)() is not None:
            return name
    return None
