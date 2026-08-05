from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from attune.core.events.schema import Event, EventType

EventHandler = Callable[[Event], Awaitable[None]]


class IEventBus(Protocol):
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None: ...

    def subscribe_all(self, handler: EventHandler) -> None: ...

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None: ...

    def unsubscribe_all(self, handler: EventHandler) -> None: ...

    async def publish(self, event: Event) -> None: ...
