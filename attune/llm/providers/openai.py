from __future__ import annotations

import httpx

from attune.llm.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            name="openai",
            base_url="https://api.openai.com/v1",
            api_key_env_var="OPENAI_API_KEY",
            model=model,
            client=client,
        )
