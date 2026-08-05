from __future__ import annotations

from attune.config.logging import configure_logging
from attune.config.settings import Settings, get_settings
from attune.container import Container
from attune.core.events.bus import EventBus
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.repository import IEventRepository, ISessionRepository, ISettingsStore
from attune.database.event_logger import EventLogger
from attune.database.repositories.event_repository import SqlAlchemyEventRepository
from attune.database.repositories.session_repository import SqlAlchemySessionRepository
from attune.database.repositories.settings_repository import SqlAlchemySettingsStore
from attune.database.session import create_engine, create_session_factory


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
    session_factory = create_session_factory(engine)

    event_repository = SqlAlchemyEventRepository(session_factory)
    session_repository = SqlAlchemySessionRepository(session_factory)
    settings_store = SqlAlchemySettingsStore(session_factory)
    container.register(IEventRepository, event_repository)  # type: ignore[type-abstract]
    container.register(ISessionRepository, session_repository)  # type: ignore[type-abstract]
    container.register(ISettingsStore, settings_store)  # type: ignore[type-abstract]

    event_bus.subscribe_all(EventLogger(event_repository).handle)

    return container
