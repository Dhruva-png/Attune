from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from attune.core.events.schema import Event, EventType
from attune.database.models import EventModel


def _to_domain(row: EventModel) -> Event:
    return Event(
        id=uuid.UUID(row.id),
        session_id=uuid.UUID(row.session_id),
        type=EventType(row.type),
        timestamp=row.timestamp,
        confidence=row.confidence,
        duration_ms=row.duration_ms,
        metadata=row.metadata_,
        source_module=row.source_module,
    )


def _to_row(event: Event) -> EventModel:
    return EventModel(
        id=str(event.id),
        session_id=str(event.session_id),
        type=event.type.value,
        timestamp=event.timestamp,
        confidence=event.confidence,
        duration_ms=event.duration_ms,
        metadata_=event.metadata,
        source_module=event.source_module,
    )


class SqlAlchemyEventRepository:
    """IEventRepository implementation. `events` is append-only — see
    docs/architecture/04-database-schema.md design notes.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, event: Event) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(_to_row(event))

    async def list(
        self,
        *,
        session_id: uuid.UUID | None = None,
        event_type: EventType | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        stmt = select(EventModel).order_by(EventModel.timestamp).limit(limit).offset(offset)
        if session_id is not None:
            stmt = stmt.where(EventModel.session_id == str(session_id))
        if event_type is not None:
            stmt = stmt.where(EventModel.type == event_type.value)
        if since is not None:
            stmt = stmt.where(EventModel.timestamp >= since)
        if until is not None:
            stmt = stmt.where(EventModel.timestamp <= until)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return [_to_domain(row) for row in result.scalars().all()]
