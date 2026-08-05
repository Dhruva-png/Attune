from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from attune.core.events.schema import Event, EventType
from attune.core.interfaces.bus import EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """In-process async pub/sub mediator. See docs/architecture/01-overview.md §3."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers[event_type].remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        self._wildcard_handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        handlers = [*self._handlers.get(event.type, []), *self._wildcard_handlers]
        if not handlers:
            return
        results = await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("Event handler failed for %s: %s", event.type, result, exc_info=result)
