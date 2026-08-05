from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from attune.core.events.schema import EventType


class TimelineEntryResponse(BaseModel):
    time: str
    label: str
    event_type: EventType
    confidence: float


class DailyReportResponse(BaseModel):
    date: date
    avg_focus_score: float | None = None
    avg_posture_score: float | None = None
    distraction_count: int
    break_count: int
    longest_break_seconds: int | None = None
    best_hours: list[str]
    worst_hours: list[str]
    timeline: list[TimelineEntryResponse]


class WeeklyReportResponse(BaseModel):
    week_start: date
    week_end: date
    avg_focus_score: float | None = None
    avg_posture_score: float | None = None
    distraction_count: int
    break_count: int
    longest_break_seconds: int | None = None
    best_hours: list[str]
    worst_hours: list[str]
    daily_breakdown: list[DailyReportResponse]
