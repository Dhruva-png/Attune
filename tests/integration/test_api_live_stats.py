from __future__ import annotations

from uuid import UUID

import pytest
from attune.api.live_session_manager import LiveSessionManager
from attune.container import Container
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_live_frame_without_active_session_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/live-stats/frame")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_live_frame_before_first_frame_is_produced_returns_404(
    api_client: AsyncClient,
) -> None:
    await api_client.post("/api/v1/start-session", json={})

    response = await api_client.get("/api/v1/live-stats/frame")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_live_frame_returns_the_latest_stored_jpeg(
    api_client: AsyncClient, api_container: Container
) -> None:
    start = await api_client.post("/api/v1/start-session", json={})
    session_id = start.json()["session_id"]

    live_session_manager = api_container.resolve(LiveSessionManager)
    fake_jpeg = b"\xff\xd8\xff\xe0not-a-real-jpeg-but-good-enough-for-a-transport-test"
    live_session_manager._latest_frames[UUID(session_id)] = fake_jpeg  # noqa: SLF001

    response = await api_client.get("/api/v1/live-stats/frame")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == fake_jpeg
