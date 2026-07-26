"""xAI Grok provider - OpenAI-compatible API."""
from __future__ import annotations

from .openai_compat import OpenAICompatProvider

_GROK_TIER = {
    "haiku": "grok-3-mini-fast",
    "sonnet": "grok-3-mini",
    "opus": "grok-3",
}

_XAI_BASE = "https://api.x.ai/v1"


class GrokProvider(OpenAICompatProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key, _GROK_TIER, base_url=_XAI_BASE, extra_name="grok")
