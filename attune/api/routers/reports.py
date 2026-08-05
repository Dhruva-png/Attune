from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP, AnalyticsEngine
from attune.analytics.timeline import TimelineEntry, build_timeline
from attune.api.dependencies import get_analytics_engine, get_event_repository
from attune.api.schemas.reports import (
    DailyReportResponse,
    TimelineEntryResponse,
    WeeklyReportResponse,
)
from attune.core.entities.analytics_snapshot import PeriodType
from attune.core.interfaces.repository import IEventRepository

router = APIRouter(tags=["reports"])


def _to_timeline_response(entries: list[TimelineEntry]) -> list[TimelineEntryResponse]:
    return [
        TimelineEntryResponse(
            time=entry.time,
            label=entry.label,
            event_type=entry.event_type,
            confidence=entry.confidence,
        )
        for entry in entries
    ]


async def _build_daily_report(
    day: date, analytics_engine: AnalyticsEngine, event_repository: IEventRepository
) -> DailyReportResponse:
    snapshot = await analytics_engine.compute_and_store(PeriodType.DAILY, day, day)
    events = await event_repository.list(
        since=datetime.combine(day, datetime.min.time()),
        until=datetime.combine(day, datetime.max.time()),
        limit=MAX_EVENTS_PER_ROLLUP,
    )
    return DailyReportResponse(
        date=day,
        avg_focus_score=snapshot.avg_focus_score,
        avg_posture_score=snapshot.avg_posture_score,
        distraction_count=snapshot.distraction_count,
        break_count=snapshot.break_count,
        longest_break_seconds=snapshot.longest_break_seconds,
        best_hours=snapshot.best_hours,
        worst_hours=snapshot.worst_hours,
        timeline=_to_timeline_response(build_timeline(events)),
    )


@router.get("/reports/daily")
async def get_daily_report(
    date: date,
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine),
    event_repository: IEventRepository = Depends(get_event_repository),
) -> DailyReportResponse:
    return await _build_daily_report(date, analytics_engine, event_repository)


@router.get("/reports/weekly")
async def get_weekly_report(
    week_start: date,
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine),
    event_repository: IEventRepository = Depends(get_event_repository),
) -> WeeklyReportResponse:
    week_end = week_start + timedelta(days=6)
    snapshot = await analytics_engine.compute_and_store(PeriodType.WEEKLY, week_start, week_end)

    daily_breakdown = [
        await _build_daily_report(
            week_start + timedelta(days=offset), analytics_engine, event_repository
        )
        for offset in range(7)
    ]

    return WeeklyReportResponse(
        week_start=week_start,
        week_end=week_end,
        avg_focus_score=snapshot.avg_focus_score,
        avg_posture_score=snapshot.avg_posture_score,
        distraction_count=snapshot.distraction_count,
        break_count=snapshot.break_count,
        longest_break_seconds=snapshot.longest_break_seconds,
        best_hours=snapshot.best_hours,
        worst_hours=snapshot.worst_hours,
        daily_breakdown=daily_breakdown,
    )
