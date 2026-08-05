from __future__ import annotations

from datetime import date, datetime
from statistics import mean
from uuid import UUID

from attune.analytics.trends import best_and_worst_hours
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.repository import IAnalyticsRepository, IEventRepository

# Generous enough for a month of continuous FOCUS_SCORE_UPDATED ticks; a real
# pagination story is unnecessary complexity until usage proves otherwise.
MAX_EVENTS_PER_ROLLUP = 200_000


def _time_weighted_posture_score(
    events: list[Event], period_start: datetime, period_end: datetime
) -> float | None:
    posture_events = sorted(
        (e for e in events if e.type in (EventType.GOOD_POSTURE, EventType.POOR_POSTURE)),
        key=lambda e: e.timestamp,
    )
    if not posture_events:
        return None

    good_seconds = 0.0
    total_seconds = 0.0
    cursor = period_start
    state_is_good = posture_events[0].type == EventType.GOOD_POSTURE

    for event in posture_events:
        segment = (event.timestamp - cursor).total_seconds()
        if segment > 0:
            total_seconds += segment
            if state_is_good:
                good_seconds += segment
        state_is_good = event.type == EventType.GOOD_POSTURE
        cursor = event.timestamp

    tail = (period_end - cursor).total_seconds()
    if tail > 0:
        total_seconds += tail
        if state_is_good:
            good_seconds += tail

    if total_seconds <= 0:
        return None
    return (good_seconds / total_seconds) * 100.0


def compute_rollup(
    events: list[Event],
    period_type: PeriodType,
    period_start: date,
    period_end: date,
    session_id: UUID | None = None,
) -> AnalyticsSnapshot:
    """Pure aggregation: a list of Events -> one AnalyticsSnapshot. No I/O,
    so it's testable with seeded fixtures — see AnalyticsEngine for the
    fetch-compute-persist orchestration.
    """
    period_start_dt = datetime.combine(period_start, datetime.min.time())
    period_end_dt = datetime.combine(period_end, datetime.max.time())

    focus_scores = [
        event.metadata["score"]
        for event in events
        if event.type == EventType.FOCUS_SCORE_UPDATED and "score" in event.metadata
    ]
    avg_focus_score = mean(focus_scores) if focus_scores else None
    avg_posture_score = _time_weighted_posture_score(events, period_start_dt, period_end_dt)

    distraction_count = sum(1 for event in events if event.type == EventType.PHONE_PICKUP)

    returned_events = [event for event in events if event.type == EventType.RETURNED]
    break_count = len(returned_events)
    break_durations_seconds = [
        event.duration_ms / 1000 for event in returned_events if event.duration_ms is not None
    ]
    longest_break_seconds = int(max(break_durations_seconds)) if break_durations_seconds else None

    best_hours, worst_hours = best_and_worst_hours(events)

    return AnalyticsSnapshot(
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        session_id=session_id,
        avg_focus_score=avg_focus_score,
        avg_posture_score=avg_posture_score,
        distraction_count=distraction_count,
        break_count=break_count,
        longest_break_seconds=longest_break_seconds,
        best_hours=best_hours,
        worst_hours=worst_hours,
        raw_metrics={"event_count": len(events), "focus_sample_count": len(focus_scores)},
    )


class AnalyticsEngine:
    """Fetches events for a period, computes the rollup, and persists it.
    Recomputing an already-stored period overwrites the previous snapshot —
    analytics_snapshots are a cache, events remain the source of truth.
    """

    def __init__(
        self, event_repository: IEventRepository, analytics_repository: IAnalyticsRepository
    ) -> None:
        self._event_repository = event_repository
        self._analytics_repository = analytics_repository

    async def compute_and_store(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        session_id: UUID | None = None,
    ) -> AnalyticsSnapshot:
        events = await self._event_repository.list(
            session_id=session_id,
            since=datetime.combine(period_start, datetime.min.time()),
            until=datetime.combine(period_end, datetime.max.time()),
            limit=MAX_EVENTS_PER_ROLLUP,
        )
        snapshot = compute_rollup(events, period_type, period_start, period_end, session_id)
        await self._analytics_repository.save(snapshot)
        return snapshot
