from __future__ import annotations

import json

import httpx
import pytest
from attune.llm.provider import LLMProviderError
from attune.llm.providers.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_sends_expected_request_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "hello there"})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    result = await provider.complete("hi", system="be nice")

    assert result == "hello there"
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["body"]["prompt"] == "hi"
    assert captured["body"]["system"] == "be nice"
    assert captured["body"]["stream"] is False


@pytest.mark.asyncio
async def test_no_api_key_needed_for_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "ok"})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await provider.complete("hi") == "ok"


@pytest.mark.asyncio
async def test_honors_ollama_host_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:9999")
    captured_url = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"response": "ok"})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await provider.complete("hi")

    assert captured_url == "http://custom-host:9999/api/generate"


@pytest.mark.asyncio
async def test_http_error_raises_llm_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="request failed"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_malformed_response_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMProviderError, match="unexpected response shape"):
        await provider.complete("hi")
