"""OpenAI (GPT) provider - text + vision."""
from __future__ import annotations

from .openai_compat import OpenAICompatProvider

_GPT_TIER = {
    "haiku": "gpt-4o-mini",
    "sonnet": "gpt-4o",
    "opus": "o3-mini",
}


class OpenAIProvider(OpenAICompatProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key, _GPT_TIER, extra_name="openai")
