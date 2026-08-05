from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from attune.core.events.schema import EventType


class EventResponse(BaseModel):
    id: UUID
    session_id: UUID
    type: EventType
    timestamp: datetime
    confidence: float
    duration_ms: int | None = None
    metadata: dict[str, Any]
    source_module: str


class EventListResponse(BaseModel):
    items: list[EventResponse]
    next_cursor: str | None = None
