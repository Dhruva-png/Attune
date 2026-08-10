from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from attune.analytics.engine import AnalyticsEngine
from attune.config.logging import configure_logging
from attune.config.settings import LLMProviderName, Settings, get_settings
from attune.container import Container
from attune.core.events.bus import EventBus
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.llm import ILLMProvider
from attune.core.interfaces.repository import (
    IAnalyticsRepository,
    IEventRepository,
    ISessionRepository,
    ISettingsStore,
)
from attune.database.event_logger import EventLogger
from attune.database.repositories.analytics_repository import SqlAlchemyAnalyticsRepository
from attune.database.repositories.event_repository import SqlAlchemyEventRepository
from attune.database.repositories.session_repository import SqlAlchemySessionRepository
from attune.database.repositories.settings_repository import SqlAlchemySettingsStore
from attune.database.session import create_engine, create_session_factory
from attune.llm.coach import AICoach
from attune.llm.factory import create_provider
from attune.reports.jobs import ReportJobStore


def bootstrap(settings: Settings | None = None) -> Container:
    """Composition root. The only module allowed to import across every layer.

    Wires concrete infrastructure implementations into the domain ports defined in
    attune.core.interfaces. Extended milestone by milestone as each layer (vision,
    database, llm, ...) is implemented — see docs/architecture/08-roadmap.md.

    Schema creation is not this function's job — run `alembic upgrade head`
    (attune/database/migrations/) before starting the app; see
    attune.database.session.init_models for the test-only shortcut.
    """
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)

    container = Container()
    # mypy flags Protocol classes as invalid `type[T]` registry keys (type-abstract);
    # structural typing makes this safe in practice — see PEP 544 / python/mypy#4717.
    event_bus = EventBus()
    container.register(IEventBus, event_bus)  # type: ignore[type-abstract]

    engine = create_engine(settings.database_url)
    container.register(AsyncEngine, engine)
    session_factory = create_session_factory(engine)

    event_repository = SqlAlchemyEventRepository(session_factory)
    session_repository = SqlAlchemySessionRepository(session_factory)
    settings_store = SqlAlchemySettingsStore(session_factory)
    analytics_repository = SqlAlchemyAnalyticsRepository(session_factory)
    container.register(IEventRepository, event_repository)  # type: ignore[type-abstract]
    container.register(ISessionRepository, session_repository)  # type: ignore[type-abstract]
    container.register(ISettingsStore, settings_store)  # type: ignore[type-abstract]
    container.register(IAnalyticsRepository, analytics_repository)  # type: ignore[type-abstract]
    container.register(AnalyticsEngine, AnalyticsEngine(event_repository, analytics_repository))

    event_bus.subscribe_all(EventLogger(event_repository).handle)

    # Ollama is local, so it needs no separate consent; any other provider is
    # "cloud AI" and only gets wired in when the user has explicitly opted in
    # (docs/architecture/01-overview.md privacy boundary) — otherwise the
    # Coach still runs, just without LLM-phrased insights.
    llm_provider: ILLMProvider | None = None
    if settings.llm.provider == LLMProviderName.OLLAMA or settings.privacy.cloud_ai_enabled:
        llm_provider = create_provider(settings.llm)
        container.register(ILLMProvider, llm_provider)  # type: ignore[type-abstract]
    container.register(AICoach, AICoach(llm_provider=llm_provider))
    container.register(ReportJobStore, ReportJobStore())

    return container
