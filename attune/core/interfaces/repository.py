from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from attune.core.entities.session import Session
from attune.core.events.schema import Event, EventType


class IEventRepository(Protocol):
    async def add(self, event: Event) -> None: ...

    async def list(
        self,
        *,
        session_id: UUID | None = None,
        event_type: EventType | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
    ) -> list[Event]: ...


class ISessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get(self, session_id: UUID) -> Session | None: ...

    async def update(self, session: Session) -> None: ...

    async def list_active(self) -> list[Session]: ...


class ISettingsStore(Protocol):
    async def load(self) -> dict[str, object]: ...

    async def save(self, values: dict[str, object]) -> None: ...
