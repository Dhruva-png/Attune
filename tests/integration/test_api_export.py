from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

import pytest
from attune.container import Container
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_session_json(api_client: AsyncClient, api_container: Container) -> None:
    session_id = uuid4()
    repository = api_container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=session_id,
            type=EventType.YAWN,
            timestamp=datetime.utcnow(),
            confidence=0.9,
            source_module="test",
        )
    )

    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "session", "target_id": str(session_id), "format": "json"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    payload = json.loads(response.content)
    assert len(payload) == 1
    assert payload[0]["type"] == "yawn"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_session_csv(api_client: AsyncClient, api_container: Container) -> None:
    session_id = uuid4()
    repository = api_container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=session_id,
            type=EventType.YAWN,
            timestamp=datetime.utcnow(),
            confidence=0.9,
            source_module="test",
        )
    )

    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "session", "target_id": str(session_id), "format": "csv"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "yawn" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_daily_scope_returns_snapshot(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "daily", "target_id": "2026-01-05", "format": "json"},
    )

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload[0]["period_type"] == "daily"
    assert payload[0]["period_start"] == "2026-01-05"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_invalid_session_id_returns_400(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "session", "target_id": "not-a-uuid", "format": "json"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_invalid_date_returns_400(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "daily", "target_id": "not-a-date", "format": "json"},
    )
    assert response.status_code == 400
