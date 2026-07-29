from __future__ import annotations

from attune.config.logging import configure_logging
from attune.config.settings import Settings, get_settings
from attune.container import Container
from attune.core.events.bus import EventBus
from attune.core.interfaces.bus import IEventBus


def bootstrap(settings: Settings | None = None) -> Container:
    """Composition root. The only module allowed to import across every layer.

    Wires concrete infrastructure implementations into the domain ports defined in
    attune.core.interfaces. Extended milestone by milestone as each layer (vision,
    database, llm, ...) is implemented — see docs/architecture/08-roadmap.md.
    """
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)

    container = Container()
    # mypy flags Protocol classes as invalid `type[T]` registry keys (type-abstract);
    # structural typing makes this safe in practice — see PEP 544 / python/mypy#4717.
    container.register(IEventBus, EventBus())  # type: ignore[type-abstract]
    return container
