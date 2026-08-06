from __future__ import annotations

import httpx
import pytest
from attune.llm.provider import LLMProviderError
from attune.llm.providers.openai_compatible import OpenAICompatibleProvider


def make_provider(handler, monkeypatch: pytest.MonkeyPatch, *, api_key: str | None = "test-key"):
    if api_key is None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TEST_API_KEY", api_key)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatibleProvider(
        name="test-provider",
        base_url="https://example.test/v1",
        api_key_env_var="TEST_API_KEY",
        model="test-model",
        client=client,
    )


@pytest.mark.asyncio
async def test_sends_expected_request_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello there"}}]})

    provider = make_provider(handler, monkeypatch)
    result = await provider.complete("hi", system="be nice")

    assert result == "hello there"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_includes_system_and_user_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["messages"] == [
            {"role": "system", "content": "be nice"},
            {"role": "user", "content": "hi"},
        ]
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = make_provider(handler, monkeypatch)
    await provider.complete("hi", system="be nice")


@pytest.mark.asyncio
async def test_omits_system_message_when_not_given(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"] == [{"role": "user", "content": "hi"}]
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = make_provider(handler, monkeypatch)
    await provider.complete("hi")


@pytest.mark.asyncio
async def test_missing_api_key_raises_without_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    provider = make_provider(handler, monkeypatch, api_key=None)

    with pytest.raises(LLMProviderError, match="TEST_API_KEY"):
        await provider.complete("hi")
    assert called is False


@pytest.mark.asyncio
async def test_http_error_status_raises_llm_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = make_provider(handler, monkeypatch)

    with pytest.raises(LLMProviderError, match="request failed"):
        await provider.complete("hi")


@pytest.mark.asyncio
async def test_malformed_response_raises_llm_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = make_provider(handler, monkeypatch)

    with pytest.raises(LLMProviderError, match="unexpected response shape"):
        await provider.complete("hi")
