from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from attune.container import Container
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository
from httpx import AsyncClient


async def _add_event(container: Container, session_id, event_type: EventType, **kwargs) -> None:
    repository = container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=session_id,
            type=event_type,
            timestamp=kwargs.pop("timestamp", datetime.utcnow()),
            confidence=kwargs.pop("confidence", 0.9),
            source_module="test",
            **kwargs,
        )
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_events_empty(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/events")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_events_filters_by_session(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_a, session_b = uuid4(), uuid4()
    await _add_event(api_container, session_a, EventType.YAWN)
    await _add_event(api_container, session_b, EventType.YAWN)

    response = await api_client.get("/api/v1/events", params={"session_id": str(session_a)})
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["session_id"] == str(session_a)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_events_filters_by_type(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_id = uuid4()
    await _add_event(api_container, session_id, EventType.YAWN)
    await _add_event(api_container, session_id, EventType.GOOD_POSTURE)

    response = await api_client.get("/api/v1/events", params={"event_type": EventType.YAWN.value})
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["type"] == "yawn"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_events_pagination_cursor(api_client: AsyncClient, api_container: Container) -> None:
    session_id = uuid4()
    for i in range(5):
        await _add_event(
            api_container, session_id, EventType.YAWN, timestamp=datetime(2026, 1, 5, 9, i)
        )

    first_page = await api_client.get("/api/v1/events", params={"limit": 2})
    assert len(first_page.json()["items"]) == 2
    cursor = first_page.json()["next_cursor"]
    assert cursor is not None

    second_page = await api_client.get("/api/v1/events", params={"limit": 2, "cursor": cursor})
    assert len(second_page.json()["items"]) == 2

    first_ids = {item["id"] for item in first_page.json()["items"]}
    second_ids = {item["id"] for item in second_page.json()["items"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_final_page_has_no_next_cursor(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_id = uuid4()
    await _add_event(api_container, session_id, EventType.YAWN)

    response = await api_client.get("/api/v1/events", params={"limit": 50})
    assert response.json()["next_cursor"] is None
