"""Provider interface. Concrete providers lazy-import their SDK so the base
library never hard-depends on any AI package."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str, tier: str, image_png: Optional[bytes] = None) -> str:
        """Return the model's text response. May include a rendered page image."""
        ...
