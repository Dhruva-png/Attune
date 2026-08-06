from __future__ import annotations

from attune.config.settings import LLMProviderName, LLMSettings
from attune.core.interfaces.llm import ILLMProvider
from attune.llm.providers.claude import ClaudeProvider
from attune.llm.providers.gemini import GeminiProvider
from attune.llm.providers.groq import GroqProvider
from attune.llm.providers.ollama import OllamaProvider
from attune.llm.providers.openai import OpenAIProvider

_PROVIDER_CLASSES: dict[LLMProviderName, type] = {
    LLMProviderName.OPENAI: OpenAIProvider,
    LLMProviderName.GEMINI: GeminiProvider,
    LLMProviderName.CLAUDE: ClaudeProvider,
    LLMProviderName.GROQ: GroqProvider,
    LLMProviderName.OLLAMA: OllamaProvider,
}


def create_provider(settings: LLMSettings) -> ILLMProvider:
    provider_class = _PROVIDER_CLASSES[settings.provider]
    return provider_class(model=settings.model)  # type: ignore[no-any-return]
