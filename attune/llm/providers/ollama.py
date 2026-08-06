from __future__ import annotations

import os
from typing import Any

import httpx

from attune.llm.provider import LLMProviderError

DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider:
    """Local inference — no API key required, matching the spec's
    privacy-first default (nothing leaves the device unless a cloud
    provider is explicitly configured).
    """

    def __init__(
        self,
        model: str = "llama3.1",
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.name = "ollama"
        self._model = model
        self._host = os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        body: dict[str, Any] = {"model": self._model, "prompt": prompt, "stream": False}
        if system:
            body["system"] = system

        try:
            response = await self._client.post(f"{self._host}/api/generate", json=body)
            response.raise_for_status()
            data = response.json()
            return str(data["response"])
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"ollama request failed: {exc}") from exc
        except KeyError as exc:
            raise LLMProviderError("ollama returned an unexpected response shape") from exc
