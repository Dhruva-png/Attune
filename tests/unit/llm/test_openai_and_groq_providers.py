from __future__ import annotations

import httpx
import pytest
from attune.llm.providers.groq import GroqProvider
from attune.llm.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_provider_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    captured_url = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    provider = OpenAIProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    assert provider.name == "openai"
    assert await provider.complete("hello") == "hi"
    assert captured_url == "https://api.openai.com/v1/chat/completions"


@pytest.mark.asyncio
async def test_groq_provider_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    captured_url = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    provider = GroqProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    assert provider.name == "groq"
    assert await provider.complete("hello") == "hi"
    assert captured_url == "https://api.groq.com/openai/v1/chat/completions"
