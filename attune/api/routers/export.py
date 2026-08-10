from __future__ import annotations

import calendar
import csv
import io
import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP, AnalyticsEngine, compute_rollup
from attune.analytics.timeline import TimelineEntry, build_timeline
from attune.api.dependencies import (
    get_analytics_engine,
    get_event_repository,
    get_report_job_store,
    get_session_repository,
)
from attune.api.schemas.export import ExportFormat, ExportJobResponse, ExportRequest, ExportScope
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.interfaces.repository import IEventRepository, ISessionRepository
from attune.reports.charts import (
    daily_average_focus_figure,
    focus_score_over_time_figure,
    render_png,
)
from attune.reports.jobs import ReportJobStore
from attune.reports.pdf_builder import build_pdf_report

router = APIRouter(tags=["export"])


def _snapshot_to_dict(snapshot: AnalyticsSnapshot) -> dict[str, Any]:
    return {
        "period_type": snapshot.period_type.value,
        "period_start": snapshot.period_start.isoformat(),
        "period_end": snapshot.period_end.isoformat(),
        "avg_focus_score": snapshot.avg_focus_score,
        "avg_posture_score": snapshot.avg_posture_score,
        "distraction_count": snapshot.distraction_count,
        "break_count": snapshot.break_count,
        "longest_break_seconds": snapshot.longest_break_seconds,
        "best_hours": snapshot.best_hours,
        "worst_hours": snapshot.worst_hours,
    }


def _parse_session_id(target_id: str) -> UUID:
    try:
        return UUID(target_id)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="target_id must be a session UUID"
        ) from exc


def _parse_date(target_id: str) -> date:
    try:
        return date.fromisoformat(target_id)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="target_id must be an ISO date"
        ) from exc


def _period_bounds(scope: ExportScope, target_date: date) -> tuple[PeriodType, date, date]:
    if scope == ExportScope.DAILY:
        return PeriodType.DAILY, target_date, target_date
    if scope == ExportScope.WEEKLY:
        return PeriodType.WEEKLY, target_date, target_date + timedelta(days=6)
    days_in_month = calendar.monthrange(target_date.year, target_date.month)[1]
    month_start = target_date.replace(day=1)
    month_end = target_date.replace(day=days_in_month)
    return PeriodType.MONTHLY, month_start, month_end


@router.post("/export")
async def export_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    event_repository: IEventRepository = Depends(get_event_repository),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine),
    session_repository: ISessionRepository = Depends(get_session_repository),
    job_store: ReportJobStore = Depends(get_report_job_store),
) -> Response:
    if request.format in (ExportFormat.PDF, ExportFormat.PNG):
        report_id = job_store.create()
        background_tasks.add_task(
            _generate_report_job,
            report_id,
            request,
            job_store,
            event_repository,
            analytics_engine,
            session_repository,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ExportJobResponse(report_id=report_id, status="processing").model_dump(
                mode="json"
            ),
        )

    if request.scope == ExportScope.SESSION:
        session_id = _parse_session_id(request.target_id)
        events = await event_repository.list(session_id=session_id, limit=MAX_EVENTS_PER_ROLLUP)
        filename_stem = f"session-{session_id}"
        payload = [event.model_dump(mode="json") for event in events]
    else:
        target_date = _parse_date(request.target_id)
        period_type, period_start, period_end = _period_bounds(request.scope, target_date)
        snapshot = await analytics_engine.compute_and_store(period_type, period_start, period_end)
        filename_stem = f"{request.scope.value}-{target_date.isoformat()}"
        payload = [_snapshot_to_dict(snapshot)]

    if request.format == ExportFormat.JSON:
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.json"'},
        )

    output = io.StringIO()
    if payload:
        writer = csv.DictWriter(output, fieldnames=list(payload[0].keys()))
        writer.writeheader()
        writer.writerows(payload)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename_stem}.csv"'},
    )


async def _resolve_report_data(
    request: ExportRequest,
    event_repository: IEventRepository,
    analytics_engine: AnalyticsEngine,
    session_repository: ISessionRepository,
) -> tuple[str, str, AnalyticsSnapshot, list[TimelineEntry], bytes | None]:
    """Returns (filename_stem, period_label, snapshot, timeline, chart_png)."""
    if request.scope == ExportScope.SESSION:
        session_id = _parse_session_id(request.target_id)
        session = await session_repository.get(session_id)
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="session not found")
        events = await event_repository.list(session_id=session_id, limit=MAX_EVENTS_PER_ROLLUP)
        period_start = session.started_at.date()
        period_end = (session.ended_at or session.started_at).date()
        snapshot = compute_rollup(
            events, PeriodType.DAILY, period_start, period_end, session_id=session_id
        )
        timeline = build_timeline(events)
        figure = focus_score_over_time_figure(events)
        chart_png = render_png(figure) if figure is not None else None
        return f"session-{session_id}", f"Session {session_id}", snapshot, timeline, chart_png

    target_date = _parse_date(request.target_id)
    period_type, period_start, period_end = _period_bounds(request.scope, target_date)
    snapshot = await analytics_engine.compute_and_store(period_type, period_start, period_end)
    filename_stem = f"{request.scope.value}-{target_date.isoformat()}"
    period_label = f"{period_start.isoformat()} to {period_end.isoformat()}"

    if request.scope == ExportScope.DAILY:
        events = await event_repository.list(
            since=datetime.combine(period_start, datetime.min.time()),
            until=datetime.combine(period_end, datetime.max.time()),
            limit=MAX_EVENTS_PER_ROLLUP,
        )
        timeline = build_timeline(events)
        figure = focus_score_over_time_figure(events)
    else:
        day_count = (period_end - period_start).days + 1
        daily_snapshots = [
            (
                period_start + timedelta(days=offset),
                await analytics_engine.compute_and_store(
                    PeriodType.DAILY,
                    period_start + timedelta(days=offset),
                    period_start + timedelta(days=offset),
                ),
            )
            for offset in range(day_count)
        ]
        timeline = []
        figure = daily_average_focus_figure(daily_snapshots)

    chart_png = render_png(figure) if figure is not None else None
    return filename_stem, period_label, snapshot, timeline, chart_png


async def _generate_report_job(
    report_id: UUID,
    request: ExportRequest,
    job_store: ReportJobStore,
    event_repository: IEventRepository,
    analytics_engine: AnalyticsEngine,
    session_repository: ISessionRepository,
) -> None:
    try:
        filename_stem, period_label, snapshot, timeline, chart_png = await _resolve_report_data(
            request, event_repository, analytics_engine, session_repository
        )

        if request.format == ExportFormat.PNG:
            if chart_png is None:
                job_store.mark_failed(report_id, "no chart data available for this period")
                return
            job_store.mark_ready(
                report_id,
                content=chart_png,
                media_type="image/png",
                filename=f"{filename_stem}.png",
            )
            return

        pdf_bytes = build_pdf_report(
            title=f"{request.scope.value.capitalize()} Report",
            period_label=period_label,
            snapshot=snapshot,
            timeline=timeline,
            chart_png=chart_png,
        )
        job_store.mark_ready(
            report_id,
            content=pdf_bytes,
            media_type="application/pdf",
            filename=f"{filename_stem}.pdf",
        )
    except HTTPException as exc:
        job_store.mark_failed(report_id, str(exc.detail))
    except Exception as exc:
        # A background task has no request/response to raise into — this is
        # the only way for generation failures to reach the polling client.
        job_store.mark_failed(report_id, str(exc))
