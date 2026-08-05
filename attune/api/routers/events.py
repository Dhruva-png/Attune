from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from attune.api.dependencies import get_event_repository
from attune.api.schemas.events import EventListResponse, EventResponse
from attune.core.events.schema import EventType
from attune.core.interfaces.repository import IEventRepository

router = APIRouter(tags=["events"])


@router.get("/events")
async def list_events(
    session_id: UUID | None = None,
    event_type: EventType | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    event_repository: IEventRepository = Depends(get_event_repository),
) -> EventListResponse:
    offset = int(cursor) if cursor is not None else 0
    events = await event_repository.list(
        session_id=session_id,
        event_type=event_type,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    next_cursor = str(offset + limit) if len(events) == limit else None
    return EventListResponse(
        items=[EventResponse.model_validate(event.model_dump()) for event in events],
        next_cursor=next_cursor,
    )
