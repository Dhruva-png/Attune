from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from attune.analytics.engine import MAX_EVENTS_PER_ROLLUP
from attune.api.dependencies import (
    get_event_bus_ws,
    get_event_repository,
    get_live_session_manager,
    get_session_repository,
)
from attune.api.live_session_manager import LiveSessionManager
from attune.api.schemas.live_stats import BreakStats, LiveStatsResponse, PhoneActivity
from attune.core.entities.fatigue import FatigueLevel
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.bus import IEventBus
from attune.core.interfaces.repository import IEventRepository, ISessionRepository

router = APIRouter(tags=["live-stats"])

HEARTBEAT_SECONDS = 2.0


def _latest(events: list[Event], event_type: EventType) -> Event | None:
    matching = [event for event in events if event.type == event_type]
    return max(matching, key=lambda event: event.timestamp) if matching else None


def _derive_status(events: list[Event]) -> str:
    left_desk = _latest(events, EventType.LEFT_DESK)
    returned = _latest(events, EventType.RETURNED)
    if left_desk is not None and (returned is None or left_desk.timestamp > returned.timestamp):
        return "away"

    pickup = _latest(events, EventType.PHONE_PICKUP)
    put_down = _latest(events, EventType.PHONE_DOWN)
    if pickup is not None and (put_down is None or pickup.timestamp > put_down.timestamp):
        return "distracted"

    return "focused"


@router.get("/live-stats")
async def get_live_stats(
    session_repository: ISessionRepository = Depends(get_session_repository),
    event_repository: IEventRepository = Depends(get_event_repository),
) -> LiveStatsResponse:
    active_sessions = await session_repository.list_active()
    if not active_sessions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no active session")
    session = max(active_sessions, key=lambda s: s.started_at)

    events = await event_repository.list(session_id=session.id, limit=MAX_EVENTS_PER_ROLLUP)

    focus_event = _latest(events, EventType.FOCUS_SCORE_UPDATED)
    fatigue_event = _latest(events, EventType.FATIGUE_LEVEL_CHANGED)
    good_posture = _latest(events, EventType.GOOD_POSTURE)
    poor_posture = _latest(events, EventType.POOR_POSTURE)

    posture = "unknown"
    latest_posture_candidates = [e for e in (good_posture, poor_posture) if e is not None]
    if latest_posture_candidates:
        latest_posture = max(latest_posture_candidates, key=lambda e: e.timestamp)
        posture = "good" if latest_posture.type == EventType.GOOD_POSTURE else "poor"

    pickups = [event for event in events if event.type == EventType.PHONE_PICKUP]
    returned_events = [event for event in events if event.type == EventType.RETURNED]
    break_durations = [
        event.duration_ms / 1000 for event in returned_events if event.duration_ms is not None
    ]

    return LiveStatsResponse(
        session_id=session.id,
        elapsed_seconds=(datetime.utcnow() - session.started_at).total_seconds(),
        focus_score=focus_event.metadata.get("score") if focus_event else None,
        status=_derive_status(events),
        fatigue_level=(FatigueLevel(fatigue_event.metadata["to_level"]) if fatigue_event else None),
        posture=posture,
        phone_activity=PhoneActivity(
            last_pickup=pickups[-1].timestamp if pickups else None,
            interactions_today=len(pickups),
        ),
        breaks=BreakStats(
            count=len(returned_events),
            total_seconds=sum(break_durations),
            longest_seconds=max(break_durations) if break_durations else 0.0,
        ),
    )


@router.get(
    "/live-stats/frame",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
async def get_live_frame(
    session_repository: ISessionRepository = Depends(get_session_repository),
    live_session_manager: LiveSessionManager = Depends(get_live_session_manager),
) -> Response:
    """Latest annotated camera frame (skeleton/mesh/hand points + phone boxes
    drawn on) for the active session, as a JPEG. The dashboard polls this on a
    short interval to render a live preview — no websocket needed since each
    poll only ever wants the newest frame, never a backlog.
    """
    active_sessions = await session_repository.list_active()
    if not active_sessions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no active session")
    session = max(active_sessions, key=lambda s: s.started_at)

    frame = live_session_manager.get_latest_frame(session.id)
    if frame is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no frame available yet")

    return Response(content=frame, media_type="image/jpeg")


@router.websocket("/live-stats/stream")
async def live_stats_stream(
    websocket: WebSocket, event_bus: IEventBus = Depends(get_event_bus_ws)
) -> None:
    """Pushes every published Event as JSON. The periodic message on an idle
    connection is a plain connection keepalive, not a synthesized focus-score
    reading — real scores only ever come from an actual running session.
    """
    await websocket.accept()
    queue: asyncio.Queue[Event] = asyncio.Queue()

    async def on_event(event: Event) -> None:
        await queue.put(event)

    event_bus.subscribe_all(on_event)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
            else:
                await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe_all(on_event)
