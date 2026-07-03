"""Anthropic (Claude) provider - the default text + vision brain."""
from __future__ import annotations

import base64
from typing import Optional

from ..router import MODEL_IDS
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:  # pragma: no cover - import guard
                raise RuntimeError(
                    "The Anthropic lane needs the 'anthropic' package: "
                    "pip install terbium-parse[anthropic]"
                ) from e
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def complete(self, prompt: str, system: str, tier: str, image_png: Optional[bytes] = None) -> str:
        model = MODEL_IDS.get(tier, MODEL_IDS["sonnet"])
        content = []
        if image_png:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(image_png).decode("ascii"),
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        msg = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
