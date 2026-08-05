from __future__ import annotations

from attune.core.events.schema import Event
from attune.core.interfaces.repository import IEventRepository


class EventLogger:
    """Subscribes to the EventBus and persists every published event — the
    write side of "events is the append-only source of truth"
    (docs/architecture/04-database-schema.md).
    """

    def __init__(self, repository: IEventRepository) -> None:
        self._repository = repository

    async def handle(self, event: Event) -> None:
        await self._repository.add(event)
