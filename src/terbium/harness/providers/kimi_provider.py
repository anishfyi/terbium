"""Moonshot Kimi provider - OpenAI-compatible API."""
from __future__ import annotations

from .openai_compat import OpenAICompatProvider

_KIMI_TIER = {
    "haiku": "kimi-k2-turbo-preview",
    "sonnet": "kimi-k2-0711-preview",
    "opus": "kimi-k2-0711-preview",
}

_MOONSHOT_BASE = "https://api.moonshot.cn/v1"


class KimiProvider(OpenAICompatProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key, _KIMI_TIER, base_url=_MOONSHOT_BASE, extra_name="kimi")
