from __future__ import annotations

import pytest
from attune.config.settings import LLMProviderName, LLMSettings
from attune.llm.factory import create_provider
from attune.llm.providers.claude import ClaudeProvider
from attune.llm.providers.gemini import GeminiProvider
from attune.llm.providers.groq import GroqProvider
from attune.llm.providers.ollama import OllamaProvider
from attune.llm.providers.openai import OpenAIProvider


@pytest.mark.parametrize(
    ("provider_name", "expected_class"),
    [
        (LLMProviderName.OPENAI, OpenAIProvider),
        (LLMProviderName.GEMINI, GeminiProvider),
        (LLMProviderName.CLAUDE, ClaudeProvider),
        (LLMProviderName.GROQ, GroqProvider),
        (LLMProviderName.OLLAMA, OllamaProvider),
    ],
)
def test_create_provider_returns_the_configured_class(
    provider_name: LLMProviderName, expected_class: type
) -> None:
    settings = LLMSettings(provider=provider_name, model="some-model")
    provider = create_provider(settings)
    assert isinstance(provider, expected_class)
    assert provider.name == provider_name.value
