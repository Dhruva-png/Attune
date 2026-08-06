from __future__ import annotations

import httpx

from attune.llm.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key_env_var="GROQ_API_KEY",
            model=model,
            client=client,
        )
