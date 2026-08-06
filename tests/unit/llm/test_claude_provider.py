from __future__ import annotations

import json

import httpx
import pytest
from attune.llm.provider import LLMProviderError
from attune.llm.providers.claude import ClaudeProvider


@pytest.mark.asyncio
async def test_sends_expected_request_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"content": [{"text": "hello there"}]})

    provider = ClaudeProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    result = await provider.complete("hi", system="be nice")

    assert result == "hello there"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"]["system"] == "be nice"
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ClaudeProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    )

    with pytest.raises(LLMProviderError, match="ANTHROPIC_API_KEY"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_http_error_raises_llm_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    provider = ClaudeProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="request failed"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_malformed_response_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = ClaudeProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="unexpected response shape"):
        await provider.complete("hi")
