from __future__ import annotations

import json

import httpx
import pytest
from attune.llm.provider import LLMProviderError
from attune.llm.providers.gemini import GeminiProvider


@pytest.mark.asyncio
async def test_sends_expected_request_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "hello there"}]}}]},
        )

    provider = GeminiProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    result = await provider.complete("hi", system="be nice")

    assert result == "hello there"
    assert "generateContent" in captured["url"]
    assert "key=test-key" in captured["url"]
    assert captured["body"]["contents"] == [{"parts": [{"text": "hi"}]}]
    assert captured["body"]["systemInstruction"] == {"parts": [{"text": "be nice"}]}


@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    )

    with pytest.raises(LLMProviderError, match="GEMINI_API_KEY"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_http_error_raises_llm_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    provider = GeminiProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="request failed"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_malformed_response_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = GeminiProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="unexpected response shape"):
        await provider.complete("hi")
