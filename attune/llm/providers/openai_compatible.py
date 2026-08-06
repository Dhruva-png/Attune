from __future__ import annotations

import os

import httpx

from attune.llm.provider import LLMProviderError


class OpenAICompatibleProvider:
    """Shared implementation for OpenAI and Groq — Groq's API deliberately
    mirrors OpenAI's /chat/completions shape, so both providers are just
    this class pointed at a different base_url/api_key/model.
    """

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key_env_var: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.name = name
        self._base_url = base_url
        self._api_key_env_var = api_key_env_var
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        api_key = os.environ.get(self._api_key_env_var)
        if not api_key:
            raise LLMProviderError(f"{self._api_key_env_var} is not set")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": self._model, "messages": messages},
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"{self.name} request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"{self.name} returned an unexpected response shape") from exc
