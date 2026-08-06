from __future__ import annotations

import os
from typing import Any

import httpx

from attune.llm.provider import LLMProviderError


class GeminiProvider:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.name = "gemini"
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is not set")

        body: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        )
        try:
            response = await self._client.post(url, params={"key": api_key}, json=body)
            response.raise_for_status()
            data = response.json()
            return str(data["candidates"][0]["content"]["parts"][0]["text"])
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"gemini request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMProviderError("gemini returned an unexpected response shape") from exc
