from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class PeriodType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class AnalyticsSnapshot:
    period_type: PeriodType
    period_start: date
    period_end: date
    id: UUID = field(default_factory=uuid4)
    session_id: UUID | None = None
    avg_focus_score: float | None = None
    avg_posture_score: float | None = None
    distraction_count: int = 0
    break_count: int = 0
    longest_break_seconds: int | None = None
    best_hours: list[str] = field(default_factory=list)
    worst_hours: list[str] = field(default_factory=list)
    raw_metrics: dict[str, Any] = field(default_factory=dict)
    computed_at: datetime = field(default_factory=datetime.utcnow)
