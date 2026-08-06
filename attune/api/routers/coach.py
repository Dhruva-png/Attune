from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP
from attune.api.dependencies import get_coach, get_event_repository
from attune.api.schemas.coach import CoachInsightResponse, CoachInsightsResponse
from attune.core.interfaces.repository import IEventRepository
from attune.llm.coach import AICoach

router = APIRouter(tags=["coach"])

_PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


@router.get("/coach/insights")
async def get_coach_insights(
    session_id: UUID | None = None,
    period: str | None = None,
    event_repository: IEventRepository = Depends(get_event_repository),
    coach: AICoach = Depends(get_coach),
) -> CoachInsightsResponse:
    if session_id is not None:
        events = await event_repository.list(session_id=session_id, limit=MAX_EVENTS_PER_ROLLUP)
    elif period is not None:
        days = _PERIOD_DAYS.get(period)
        if days is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="period must be daily, weekly, or monthly"
            )
        until = datetime.utcnow()
        since = until - timedelta(days=days)
        events = await event_repository.list(since=since, until=until, limit=MAX_EVENTS_PER_ROLLUP)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="must provide session_id or period")

    insights = await coach.generate_insights(events)

    return CoachInsightsResponse(
        insights=[
            CoachInsightResponse(
                text=insight.text,
                confidence=insight.confidence,
                evidence_event_ids=list(insight.evidence_event_ids),
            )
            for insight in insights
        ],
        generated_by=coach.generated_by,
        generated_at=datetime.utcnow(),
    )
