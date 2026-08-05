from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from attune.api.main import create_app
from attune.bootstrap import bootstrap
from attune.config.settings import Settings
from attune.container import Container
from attune.database.session import init_models
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest_asyncio.fixture
async def api_container(tmp_path: Path) -> AsyncIterator[Container]:
    db_path = tmp_path / "attune_api_test.db"
    settings = Settings(database_url=f"sqlite+aiosqlite:///{db_path}")
    container = bootstrap(settings)
    engine = container.resolve(AsyncEngine)
    await init_models(engine)
    yield container
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(api_container: Container) -> AsyncIterator[AsyncClient]:
    app = create_app(container=api_container)
    # Plain ASGITransport doesn't run the lifespan, so app.state.container
    # (normally set there) is assigned directly instead.
    app.state.container = api_container

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
