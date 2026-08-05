from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from attune.api.main import create_app
from attune.bootstrap import bootstrap
from attune.config.settings import Settings
from attune.container import Container
from attune.database.session import init_models
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

# TestClient runs the ASGI app in a background thread with its own event
# loop. Publishing events from the test itself (a different loop) would hit
# cross-loop asyncio errors — every trigger below goes through another
# client.post() call instead, so it executes on the app's own loop, same as
# the websocket handler.


@pytest.fixture
def ws_client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "attune_ws_test.db"
    settings = Settings(database_url=f"sqlite+aiosqlite:///{db_path}")
    container: Container = bootstrap(settings)
    engine = container.resolve(AsyncEngine)
    asyncio.run(init_models(engine))

    app = create_app(container=container)
    with TestClient(app) as client:
        yield client

    asyncio.run(engine.dispose())


@pytest.mark.integration
def test_websocket_receives_a_published_event(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/api/v1/live-stats/stream") as websocket:
        ws_client.post("/api/v1/start-session", json={})
        message = websocket.receive_json()

    assert message["type"] == "session_started"


@pytest.mark.integration
def test_websocket_sends_heartbeat_when_idle(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/api/v1/live-stats/stream") as websocket:
        message = websocket.receive_json()  # nothing published; waits out HEARTBEAT_SECONDS

    assert message == {"type": "heartbeat"}
