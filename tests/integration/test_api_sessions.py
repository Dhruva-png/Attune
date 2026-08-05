from __future__ import annotations

from datetime import datetime

import pytest
from attune.container import Container
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_session_creates_active_session(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/start-session", json={"camera_index": 0})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["ended_at"] is None
    assert body["focus_score_avg"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_session_publishes_session_started_event(api_client: AsyncClient) -> None:
    start = await api_client.post("/api/v1/start-session", json={})
    session_id = start.json()["session_id"]

    events = await api_client.get("/api/v1/events", params={"session_id": session_id})
    types = [item["type"] for item in events.json()["items"]]

    assert "session_started" in types


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_session_marks_completed(api_client: AsyncClient) -> None:
    start = await api_client.post("/api/v1/start-session", json={})
    session_id = start.json()["session_id"]

    end = await api_client.post("/api/v1/end-session", json={"session_id": session_id})

    assert end.status_code == 200
    body = end.json()
    assert body["status"] == "completed"
    assert body["ended_at"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_session_missing_session_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/end-session", json={"session_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_session_twice_returns_409(api_client: AsyncClient) -> None:
    start = await api_client.post("/api/v1/start-session", json={})
    session_id = start.json()["session_id"]
    await api_client.post("/api/v1/end-session", json={"session_id": session_id})

    second = await api_client.post("/api/v1/end-session", json={"session_id": session_id})
    assert second.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_session_computes_scores_from_recorded_events(
    api_client: AsyncClient, api_container: Container
) -> None:
    start = await api_client.post("/api/v1/start-session", json={})
    session_id = start.json()["session_id"]

    event_repository = api_container.resolve(IEventRepository)
    await event_repository.add(
        Event(
            session_id=session_id,
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime.utcnow(),
            confidence=1.0,
            metadata={"score": 77.5},
            source_module="test",
        )
    )

    end = await api_client.post("/api/v1/end-session", json={"session_id": session_id})

    assert end.json()["focus_score_avg"] == 77.5
