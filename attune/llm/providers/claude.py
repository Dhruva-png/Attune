from __future__ import annotations

import os
from typing import Any

import httpx

from attune.llm.provider import LLMProviderError

ANTHROPIC_VERSION = "2023-06-01"
MAX_TOKENS = 1024


class ClaudeProvider:
    def __init__(
        self,
        model: str = "claude-sonnet-5",
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.name = "claude"
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY is not set")

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        try:
            response = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["content"][0]["text"])
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"claude request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMProviderError("claude returned an unexpected response shape") from exc
