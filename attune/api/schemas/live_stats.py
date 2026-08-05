from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from attune.core.entities.fatigue import FatigueLevel


class PhoneActivity(BaseModel):
    last_pickup: datetime | None = None
    interactions_today: int = 0


class BreakStats(BaseModel):
    count: int = 0
    total_seconds: float = 0.0
    longest_seconds: float = 0.0


class LiveStatsResponse(BaseModel):
    session_id: UUID
    elapsed_seconds: float
    focus_score: float | None = None
    status: Literal["focused", "distracted", "away"] = "focused"
    fatigue_level: FatigueLevel | None = None
    posture: Literal["good", "poor", "unknown"] = "unknown"
    phone_activity: PhoneActivity
    breaks: BreakStats
