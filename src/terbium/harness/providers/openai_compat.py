"""Shared OpenAI-compatible chat client (OpenAI, Kimi/Moonshot, Grok/xAI)."""
from __future__ import annotations

import base64
import re
from typing import Dict, Optional

from .base import LLMProvider


def _is_o_series(model: str) -> bool:
    """True for OpenAI o-series reasoning models (o1, o3-mini, o4-mini, ...)."""
    return bool(re.match(r"o\d", model or ""))


class OpenAICompatProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        tier_models: Dict[str, str],
        *,
        base_url: Optional[str] = None,
        extra_name: str = "openai",
    ):
        self.api_key = api_key
        self.tier_models = tier_models
        self.base_url = base_url
        self.extra_name = extra_name
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:  # pragma: no cover - import guard
                raise RuntimeError(
                    f"The {self.extra_name} lane needs the 'openai' package: "
                    f"pip install terbium-parse[{self.extra_name}]"
                ) from e
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(self, prompt: str, system: str, tier: str, image_png: Optional[bytes] = None) -> str:
        model = self.tier_models.get(tier, self.tier_models.get("sonnet", next(iter(self.tier_models.values()))))
        content = []
        if image_png:
            b64 = base64.b64encode(image_png).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
        content.append({"type": "text", "text": prompt})
        # o-series reasoning models reject max_tokens; the openai SDK documents
        # max_completion_tokens (openai>=1.45) as the replacement.
        limit = {"max_completion_tokens": 4096} if _is_o_series(model) else {"max_tokens": 4096}
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            **limit,
        )
        return resp.choices[0].message.content or ""
