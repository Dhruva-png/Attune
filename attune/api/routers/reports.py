from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP, AnalyticsEngine
from attune.analytics.timeline import TimelineEntry, build_timeline
from attune.api.dependencies import get_analytics_engine, get_event_repository, get_report_job_store
from attune.api.schemas.export import ReportStatusResponse
from attune.api.schemas.reports import (
    DailyReportResponse,
    TimelineEntryResponse,
    WeeklyReportResponse,
)
from attune.core.entities.analytics_snapshot import PeriodType
from attune.core.interfaces.repository import IEventRepository
from attune.reports.jobs import ReportJobStatus, ReportJobStore

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


@router.get("/reports/{report_id}")
async def get_report_status(
    report_id: UUID,
    job_store: ReportJobStore = Depends(get_report_job_store),
) -> ReportStatusResponse:
    """Polling endpoint for the async PDF/PNG jobs POST /export creates."""
    job = job_store.get(report_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="report not found")

    if job.status == ReportJobStatus.READY:
        return ReportStatusResponse(
            status="ready", download_url=f"/api/v1/reports/{report_id}/download"
        )
    if job.status == ReportJobStatus.FAILED:
        return ReportStatusResponse(status="failed", error=job.error)
    return ReportStatusResponse(status="processing")


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: UUID,
    job_store: ReportJobStore = Depends(get_report_job_store),
) -> Response:
    job = job_store.get(report_id)
    if job is None or job.status != ReportJobStatus.READY or job.content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="report not ready")

    return Response(
        content=job.content,
        media_type=job.media_type,
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )
