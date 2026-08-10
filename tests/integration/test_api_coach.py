from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from attune.container import Container
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository
from httpx import AsyncClient


async def _add_event(
    container: Container, session_id, event_type: EventType, when, **kwargs
) -> None:
    repository = container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=session_id,
            type=event_type,
            timestamp=when,
            confidence=kwargs.pop("confidence", 0.9),
            source_module="test",
            **kwargs,
        )
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_requires_session_id_or_period(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/coach/insights")
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rejects_invalid_period(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/coach/insights", params={"period": "yearly"})
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_with_no_events_returns_no_insights(api_client: AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/coach/insights", params={"session_id": str(uuid4())}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["insights"] == []
    assert "generated_at" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_with_phone_pattern_returns_evidence_backed_insight(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_id = uuid4()
    base = datetime(2026, 1, 5, 9, 0)

    for i in range(3):
        pickup_time = base + timedelta(hours=i)
        await _add_event(
            api_container,
            session_id,
            EventType.FOCUS_SCORE_UPDATED,
            pickup_time - timedelta(minutes=1),
            metadata={"score": 80.0},
        )
        await _add_event(api_container, session_id, EventType.PHONE_PICKUP, pickup_time)
        await _add_event(
            api_container,
            session_id,
            EventType.FOCUS_SCORE_UPDATED,
            pickup_time + timedelta(minutes=2),
            metadata={"score": 50.0},
        )

    response = await api_client.get(
        "/api/v1/coach/insights", params={"session_id": str(session_id)}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["insights"]) >= 1
    phone_insight = next(i for i in body["insights"] if "phone" in i["text"].lower())
    assert phone_insight["confidence"] > 0
    assert len(phone_insight["evidence_event_ids"]) == 3
    # generated_by reflects the fallback path when no LLM is actually reachable
    assert body["generated_by"] in {"ollama", "deterministic"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_period_query_scopes_to_recent_events(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_id = uuid4()
    recent = datetime.utcnow() - timedelta(hours=1)

    await _add_event(
        api_container,
        session_id,
        EventType.FOCUS_SCORE_UPDATED,
        recent,
        metadata={"score": 90.0},
    )

    response = await api_client.get("/api/v1/coach/insights", params={"period": "weekly"})

    assert response.status_code == 200
    assert response.json()["insights"] == []  # one sample point isn't enough to detect a pattern
