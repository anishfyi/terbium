"""Google Gemini provider - used for the vision lane and as a text fallback.

Note on Nano Banana: Gemini 2.5 Flash Image ("Nano Banana") is an image
generation/editing model, not an extraction one. terbium uses a Gemini *vision*
model to read icons and swatches; Nano Banana is reserved for optional image
normalization and is not wired into the parse path.
"""
from __future__ import annotations

from typing import Optional

from .base import LLMProvider

_GEMINI_TIER = {
    "haiku": "gemini-2.5-flash",
    "sonnet": "gemini-2.5-flash",
    "opus": "gemini-2.5-pro",
}


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._genai = None

    @property
    def genai(self):
        if self._genai is None:
            try:
                import google.generativeai as genai
            except ImportError as e:  # pragma: no cover - import guard
                raise RuntimeError(
                    "The Gemini lane needs 'google-generativeai': "
                    "pip install terbium-parse[gemini]"
                ) from e
            genai.configure(api_key=self.api_key)
            self._genai = genai
        return self._genai

    def complete(self, prompt: str, system: str, tier: str, image_png: Optional[bytes] = None) -> str:
        model_name = _GEMINI_TIER.get(tier, "gemini-2.5-flash")
        model = self.genai.GenerativeModel(model_name, system_instruction=system)
        parts = []
        if image_png:
            parts.append({"mime_type": "image/png", "data": image_png})
        parts.append(prompt)
        resp = model.generate_content(parts)
        return resp.text or ""
