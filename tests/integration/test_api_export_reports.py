from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from attune.container import Container
from attune.core.entities.session import Session, SessionStatus
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IEventRepository, ISessionRepository
from httpx import AsyncClient


async def _wait_for_ready(api_client: AsyncClient, report_id: str, timeout: float = 5.0) -> dict:
    elapsed = 0.0
    step = 0.02
    while elapsed < timeout:
        response = await api_client.get(f"/api/v1/reports/{report_id}")
        body = response.json()
        if body["status"] != "processing":
            return body
        await asyncio.sleep(step)
        elapsed += step
    raise AssertionError(f"report {report_id} never left 'processing' within {timeout}s")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_pdf_returns_202_then_ready_then_downloads(
    api_client: AsyncClient, api_container: Container
) -> None:
    repository = api_container.resolve(IEventRepository)
    session_id = uuid4()
    await repository.add(
        Event(
            session_id=session_id,
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime(2026, 1, 5, 9, 0),
            confidence=0.9,
            metadata={"score": 75.0},
            source_module="test",
        )
    )

    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "daily", "target_id": "2026-01-05", "format": "pdf"},
    )
    assert response.status_code == 202
    report_id = response.json()["report_id"]
    assert response.json()["status"] == "processing"

    status_body = await _wait_for_ready(api_client, report_id)
    assert status_body["status"] == "ready"
    assert status_body["download_url"] == f"/api/v1/reports/{report_id}/download"

    download = await api_client.get(status_body["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF-")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_png_for_session_scope(
    api_client: AsyncClient, api_container: Container
) -> None:
    session_repository = api_container.resolve(ISessionRepository)
    event_repository = api_container.resolve(IEventRepository)
    session = Session(
        id=uuid4(),
        started_at=datetime(2026, 1, 5, 9, 0),
        ended_at=datetime(2026, 1, 5, 10, 0),
        status=SessionStatus.COMPLETED,
    )
    await session_repository.add(session)
    await event_repository.add(
        Event(
            session_id=session.id,
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime(2026, 1, 5, 9, 30),
            confidence=0.9,
            metadata={"score": 60.0},
            source_module="test",
        )
    )

    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "session", "target_id": str(session.id), "format": "png"},
    )
    assert response.status_code == 202
    report_id = response.json()["report_id"]

    status_body = await _wait_for_ready(api_client, report_id)
    assert status_body["status"] == "ready"

    download = await api_client.get(status_body["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"
    assert download.content.startswith(b"\x89PNG")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_png_with_no_data_marks_job_failed(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "daily", "target_id": "2026-02-01", "format": "png"},
    )
    report_id = response.json()["report_id"]

    status_body = await _wait_for_ready(api_client, report_id)

    assert status_body["status"] == "failed"
    assert status_body["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_report_status_unknown_id_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/reports/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_report_before_ready_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/reports/{uuid4()}/download")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_monthly_scope_returns_snapshot(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "monthly", "target_id": "2026-01-15", "format": "json"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["period_type"] == "monthly"
    assert payload[0]["period_start"] == "2026-01-01"
    assert payload[0]["period_end"] == "2026-01-31"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_pdf_for_weekly_scope(
    api_client: AsyncClient, api_container: Container
) -> None:
    repository = api_container.resolve(IEventRepository)
    await repository.add(
        Event(
            session_id=uuid4(),
            type=EventType.FOCUS_SCORE_UPDATED,
            timestamp=datetime(2026, 1, 6, 9, 0),
            confidence=0.9,
            metadata={"score": 55.0},
            source_module="test",
        )
    )

    response = await api_client.post(
        "/api/v1/export",
        json={"scope": "weekly", "target_id": "2026-01-05", "format": "pdf"},
    )
    report_id = response.json()["report_id"]

    status_body = await _wait_for_ready(api_client, report_id)

    assert status_body["status"] == "ready"
    download = await api_client.get(status_body["download_url"])
    assert download.content.startswith(b"%PDF-")
