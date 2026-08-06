from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from attune.api.routers import coach, events, export, live_stats, reports, sessions, settings
from attune.bootstrap import bootstrap
from attune.config.settings import get_settings
from attune.container import Container

API_V1_PREFIX = "/api/v1"


def create_app(container: Container | None = None) -> FastAPI:
    """App factory. Pass a pre-built `container` (e.g. wired to a temp test
    database) to skip the default bootstrap() call in the lifespan — this is
    what makes the API testable via httpx without touching the real DB.
    """
    owns_container = container is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or bootstrap()
        yield
        if owns_container:
            engine = app.state.container.resolve(AsyncEngine)
            await engine.dispose()

    app = FastAPI(
        title="Attune API",
        description=(
            "Local HTTP/WebSocket API for the Attune desktop app — session "
            "lifecycle, events, analytics reports, settings, and export. "
            "See docs/architecture/06-api-specification.md."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(sessions.router, prefix=API_V1_PREFIX)
    app.include_router(live_stats.router, prefix=API_V1_PREFIX)
    app.include_router(events.router, prefix=API_V1_PREFIX)
    app.include_router(reports.router, prefix=API_V1_PREFIX)
    app.include_router(settings.router, prefix=API_V1_PREFIX)
    app.include_router(export.router, prefix=API_V1_PREFIX)
    app.include_router(coach.router, prefix=API_V1_PREFIX)

    return app


app = create_app()


def run() -> None:
    app_settings = get_settings()
    uvicorn.run(app, host=app_settings.api_host, port=app_settings.api_port)
