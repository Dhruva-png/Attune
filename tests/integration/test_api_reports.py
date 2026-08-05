from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from attune.container import Container
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository
from httpx import AsyncClient


async def _add_event(container: Container, event_type: EventType, hour: int, **kwargs) -> None:
    repository = container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=kwargs.pop("session_id", uuid4()),
            type=event_type,
            timestamp=datetime(2026, 1, 5, hour, kwargs.pop("minute", 0)),
            confidence=kwargs.pop("confidence", 0.9),
            source_module="test",
            **kwargs,
        )
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_report_with_no_data(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/reports/daily", params={"date": "2026-01-05"})

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-01-05"
    assert body["avg_focus_score"] is None
    assert body["timeline"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_report_reflects_recorded_events(
    api_client: AsyncClient, api_container: Container
) -> None:
    await _add_event(api_container, EventType.FOCUS_SCORE_UPDATED, hour=9, metadata={"score": 80.0})
    await _add_event(api_container, EventType.SESSION_STARTED, hour=9)
    await _add_event(api_container, EventType.PHONE_PICKUP, hour=9, minute=15)

    response = await api_client.get("/api/v1/reports/daily", params={"date": "2026-01-05"})
    body = response.json()

    assert body["avg_focus_score"] == 80.0
    assert body["distraction_count"] == 1
    labels = [entry["label"] for entry in body["timeline"]]
    assert "Started" in labels
    assert "Phone Pickup" in labels
    # FOCUS_SCORE_UPDATED is filtered out of the default timeline (continuous, not a moment)
    assert "Focus Score Updated" not in labels


@pytest.mark.integration
@pytest.mark.asyncio
async def test_weekly_report_includes_seven_day_breakdown(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/reports/weekly", params={"week_start": "2026-01-05"})

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-01-05"
    assert body["week_end"] == "2026-01-11"
    assert len(body["daily_breakdown"]) == 7
    assert body["daily_breakdown"][0]["date"] == "2026-01-05"
    assert body["daily_breakdown"][6]["date"] == "2026-01-11"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_weekly_report_aggregates_across_the_whole_week(
    api_client: AsyncClient, api_container: Container
) -> None:
    await _add_event(api_container, EventType.FOCUS_SCORE_UPDATED, hour=9, metadata={"score": 60.0})
    repository = api_container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=uuid4(),
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime(2026, 1, 8, 9, 0),
            confidence=0.9,
            metadata={"score": 100.0},
            source_module="test",
        )
    )

    response = await api_client.get("/api/v1/reports/weekly", params={"week_start": "2026-01-05"})
    assert response.json()["avg_focus_score"] == 80.0
