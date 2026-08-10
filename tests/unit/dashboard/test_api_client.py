from __future__ import annotations

from datetime import date
from uuid import uuid4

import httpx
import pytest
from attune.dashboard.api_client import ApiClient


def _client_with(handler) -> ApiClient:  # type: ignore[no-untyped-def]
    client = ApiClient("http://testserver")
    client._client = httpx.AsyncClient(
        base_url="http://testserver", transport=httpx.MockTransport(handler)
    )
    return client


@pytest.mark.asyncio
async def test_start_session_posts_camera_index() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(201, json={"session_id": "abc", "status": "active"})

    client = _client_with(handler)
    result = await client.start_session(camera_index=1)

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/v1/start-session")
    assert b'"camera_index":1' in captured["body"]
    assert result == {"session_id": "abc", "status": "active"}


@pytest.mark.asyncio
async def test_end_session_posts_session_id() -> None:
    session_id = uuid4()
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json={"status": "ended"})

    client = _client_with(handler)
    await client.end_session(session_id)

    assert str(session_id).encode() in captured["body"]


@pytest.mark.asyncio
async def test_get_live_stats_returns_none_on_404() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = _client_with(handler)
    assert await client.get_live_stats() is None


@pytest.mark.asyncio
async def test_get_live_stats_returns_body_on_200() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"focus_score": 80.0})

    client = _client_with(handler)
    assert await client.get_live_stats() == {"focus_score": 80.0}


@pytest.mark.asyncio
async def test_list_events_forwards_params() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={"items": [], "next_cursor": None})

    client = _client_with(handler)
    await client.list_events(limit=10, event_type="yawn")

    assert captured["query"] == {"limit": "10", "event_type": "yawn"}


@pytest.mark.asyncio
async def test_get_daily_report_formats_date() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={})

    client = _client_with(handler)
    await client.get_daily_report(date(2026, 1, 5))

    assert captured["query"]["date"] == "2026-01-05"


@pytest.mark.asyncio
async def test_get_weekly_report_formats_week_start() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={})

    client = _client_with(handler)
    await client.get_weekly_report(date(2026, 1, 5))

    assert captured["query"]["week_start"] == "2026-01-05"


@pytest.mark.asyncio
async def test_update_settings_puts_payload() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.content
        return httpx.Response(200, json={"llm_provider": "ollama"})

    client = _client_with(handler)
    result = await client.update_settings({"llm_provider": "ollama"})

    assert captured["method"] == "PUT"
    assert b"ollama" in captured["body"]
    assert result == {"llm_provider": "ollama"}


@pytest.mark.asyncio
async def test_get_coach_insights_omits_unset_params() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={"insights": []})

    client = _client_with(handler)
    await client.get_coach_insights(period="weekly")

    assert captured["query"] == {"period": "weekly"}


@pytest.mark.asyncio
async def test_get_coach_insights_includes_session_id_when_set() -> None:
    session_id = uuid4()
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={"insights": []})

    client = _client_with(handler)
    await client.get_coach_insights(session_id=session_id)

    assert captured["query"] == {"session_id": str(session_id)}


@pytest.mark.asyncio
async def test_error_response_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _client_with(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_settings()
