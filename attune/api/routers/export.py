from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP, AnalyticsEngine
from attune.api.dependencies import get_analytics_engine, get_event_repository
from attune.api.schemas.export import ExportFormat, ExportRequest, ExportScope
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.interfaces.repository import IEventRepository

router = APIRouter(tags=["export"])

# Full PDF/PNG generation (with its own async job + polling flow, per
# docs/architecture/06-api-specification.md) needs the report/chart-rendering
# infrastructure from M11. This endpoint covers synchronous JSON/CSV export
# only for now — the data that's actually available today.


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


@router.post("/export")
async def export_data(
    request: ExportRequest,
    event_repository: IEventRepository = Depends(get_event_repository),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> Response:
    if request.scope == ExportScope.SESSION:
        try:
            session_id = UUID(request.target_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="target_id must be a session UUID"
            ) from exc
        events = await event_repository.list(session_id=session_id, limit=MAX_EVENTS_PER_ROLLUP)
        filename_stem = f"session-{session_id}"
        payload = [event.model_dump(mode="json") for event in events]
    else:
        try:
            target_date = date.fromisoformat(request.target_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="target_id must be an ISO date"
            ) from exc
        period_type = PeriodType.DAILY if request.scope == ExportScope.DAILY else PeriodType.WEEKLY
        period_end = (
            target_date if period_type == PeriodType.DAILY else target_date + timedelta(days=6)
        )
        snapshot = await analytics_engine.compute_and_store(period_type, target_date, period_end)
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
