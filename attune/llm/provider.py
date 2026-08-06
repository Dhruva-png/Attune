from __future__ import annotations

from attune.core.interfaces.llm import ILLMProvider

__all__ = ["ILLMProvider", "LLMProviderError"]


class LLMProviderError(Exception):
    """Raised when a provider's HTTP call fails or its response can't be parsed."""
