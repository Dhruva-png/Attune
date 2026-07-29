from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from attune.core.entities.fatigue import FatigueLevel
from attune.core.exceptions import InvalidSessionStateError


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass(slots=True)
class Session:
    id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    focus_score_avg: float | None = None
    posture_score_avg: float | None = None
    fatigue_level_end: FatigueLevel | None = None

    def end(self, at: datetime | None = None) -> None:
        if self.status != SessionStatus.ACTIVE:
            raise InvalidSessionStateError(f"cannot end a session with status {self.status}")
        self.ended_at = at or datetime.utcnow()
        self.status = SessionStatus.COMPLETED

    def abort(self, at: datetime | None = None) -> None:
        if self.status != SessionStatus.ACTIVE:
            raise InvalidSessionStateError(f"cannot abort a session with status {self.status}")
        self.ended_at = at or datetime.utcnow()
        self.status = SessionStatus.ABORTED
