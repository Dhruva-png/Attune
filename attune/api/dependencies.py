from __future__ import annotations

from fastapi import Request, WebSocket

from attune.analytics.engine import AnalyticsEngine
from attune.api.live_session_manager import LiveSessionManager
from attune.container import Container
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.repository import (
    IAnalyticsRepository,
    IEventRepository,
    ISessionRepository,
    ISettingsStore,
)
from attune.llm.coach import AICoach
from attune.reports.jobs import ReportJobStore


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]


def get_event_bus(request: Request) -> IEventBus:
    return get_container(request).resolve(IEventBus)  # type: ignore[type-abstract]


def get_event_repository(request: Request) -> IEventRepository:
    return get_container(request).resolve(IEventRepository)  # type: ignore[type-abstract]


def get_session_repository(request: Request) -> ISessionRepository:
    return get_container(request).resolve(ISessionRepository)  # type: ignore[type-abstract]


def get_settings_store(request: Request) -> ISettingsStore:
    return get_container(request).resolve(ISettingsStore)  # type: ignore[type-abstract]


def get_analytics_repository(request: Request) -> IAnalyticsRepository:
    return get_container(request).resolve(IAnalyticsRepository)  # type: ignore[type-abstract]


def get_analytics_engine(request: Request) -> AnalyticsEngine:
    return get_container(request).resolve(AnalyticsEngine)


def get_coach(request: Request) -> AICoach:
    return get_container(request).resolve(AICoach)


def get_report_job_store(request: Request) -> ReportJobStore:
    return get_container(request).resolve(ReportJobStore)


def get_live_session_manager(request: Request) -> LiveSessionManager:
    return get_container(request).resolve(LiveSessionManager)


# WebSocket routes get a WebSocket connection scope, not a Request — FastAPI
# cannot satisfy a Request-typed dependency there, so the WS router needs
# its own variant of anything it depends on.
def get_event_bus_ws(websocket: WebSocket) -> IEventBus:
    container: Container = websocket.app.state.container
    return container.resolve(IEventBus)  # type: ignore[type-abstract]
