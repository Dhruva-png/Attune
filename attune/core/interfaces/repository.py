from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
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
        offset: int = 0,
    ) -> list[Event]: ...


class ISessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get(self, session_id: UUID) -> Session | None: ...

    async def update(self, session: Session) -> None: ...

    async def list_active(self) -> list[Session]: ...


class ISettingsStore(Protocol):
    async def load(self) -> dict[str, object]: ...

    async def save(self, values: dict[str, object]) -> None: ...


class IAnalyticsRepository(Protocol):
    async def save(self, snapshot: AnalyticsSnapshot) -> None: ...

    async def get(
        self, period_type: PeriodType, period_start: date, session_id: UUID | None = None
    ) -> AnalyticsSnapshot | None: ...

    async def list(
        self, period_type: PeriodType, session_id: UUID | None = None
    ) -> list[AnalyticsSnapshot]: ...
