from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from attune.core.entities.fatigue import FatigueLevel
from attune.core.entities.session import SessionStatus


class StartSessionRequest(BaseModel):
    camera_index: int = 0
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class EndSessionRequest(BaseModel):
    session_id: UUID


class SessionResponse(BaseModel):
    session_id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    status: SessionStatus
    focus_score_avg: float | None = None
    posture_score_avg: float | None = None
    fatigue_level_end: FatigueLevel | None = None
