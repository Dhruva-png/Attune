from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP, compute_rollup
from attune.api.dependencies import (
    get_event_bus,
    get_event_repository,
    get_live_session_manager,
    get_session_repository,
)
from attune.api.live_session_manager import LiveSessionManager
from attune.api.schemas.session import EndSessionRequest, SessionResponse, StartSessionRequest
from attune.core.entities.analytics_snapshot import PeriodType
from attune.core.entities.fatigue import FatigueLevel
from attune.core.entities.session import Session, SessionStatus
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.repository import IEventRepository, ISessionRepository

router = APIRouter(tags=["sessions"])


def _to_response(session: Session) -> SessionResponse:
    return SessionResponse(
        session_id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        focus_score_avg=session.focus_score_avg,
        posture_score_avg=session.posture_score_avg,
        fatigue_level_end=session.fatigue_level_end,
    )


@router.post("/start-session", status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartSessionRequest,
    session_repository: ISessionRepository = Depends(get_session_repository),
    event_bus: IEventBus = Depends(get_event_bus),
    live_session_manager: LiveSessionManager = Depends(get_live_session_manager),
) -> SessionResponse:
    session = Session()
    await session_repository.add(session)
    await event_bus.publish(
        Event(
            session_id=session.id,
            type=EventType.SESSION_STARTED,
            confidence=1.0,
            metadata={"camera_index": request.camera_index},
            source_module="api.sessions",
        )
    )
    live_session_manager.start(session.id, request.camera_index)
    return _to_response(session)


@router.post("/end-session")
async def end_session(
    request: EndSessionRequest,
    session_repository: ISessionRepository = Depends(get_session_repository),
    event_repository: IEventRepository = Depends(get_event_repository),
    event_bus: IEventBus = Depends(get_event_bus),
    live_session_manager: LiveSessionManager = Depends(get_live_session_manager),
) -> SessionResponse:
    session = await session_repository.get(request.session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"session is {session.status.value}, not active"
        )

    await live_session_manager.stop(session.id)

    events = await event_repository.list(session_id=session.id, limit=MAX_EVENTS_PER_ROLLUP)
    day = session.started_at.date()
    rollup = compute_rollup(events, PeriodType.DAILY, day, day, session.id)

    fatigue_events = [e for e in events if e.type == EventType.FATIGUE_LEVEL_CHANGED]
    if fatigue_events:
        latest_fatigue = max(fatigue_events, key=lambda e: e.timestamp)
        session.fatigue_level_end = FatigueLevel(latest_fatigue.metadata["to_level"])

    session.focus_score_avg = rollup.avg_focus_score
    session.posture_score_avg = rollup.avg_posture_score
    session.end()

    await session_repository.update(session)
    await event_bus.publish(
        Event(
            session_id=session.id,
            type=EventType.SESSION_ENDED,
            confidence=1.0,
            source_module="api.sessions",
        )
    )
    return _to_response(session)
