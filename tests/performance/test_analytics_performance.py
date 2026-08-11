from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from attune.analytics.engine import compute_rollup
from attune.core.entities.analytics_snapshot import PeriodType
from attune.core.events.schema import Event, EventType

# Comfortably below MAX_EVENTS_PER_ROLLUP (200_000) — a stress case, not the
# ceiling, since the ceiling is meant as a sanity cap rather than a realistic
# single-period volume.
EVENT_COUNT = 100_000
ROLLUP_BUDGET_SECONDS = 2.0


def _synthetic_month_of_events() -> list[Event]:
    session_id = uuid4()
    start = datetime(2026, 1, 1)
    events: list[Event] = []
    for i in range(EVENT_COUNT):
        timestamp = start + timedelta(seconds=i * 10)
        if i % 5 == 0:
            event_type = EventType.GOOD_POSTURE if i % 10 == 0 else EventType.POOR_POSTURE
            events.append(
                Event(
                    session_id=session_id,
                    type=event_type,
                    timestamp=timestamp,
                    confidence=0.9,
                    source_module="perf-test",
                )
            )
        else:
            events.append(
                Event(
                    session_id=session_id,
                    type=EventType.FOCUS_SCORE_UPDATED,
                    timestamp=timestamp,
                    confidence=0.9,
                    metadata={"score": 50.0 + (i % 50)},
                    source_module="perf-test",
                )
            )
    return events


@pytest.mark.performance
def test_compute_rollup_meets_latency_budget_at_high_event_volume() -> None:
    events = _synthetic_month_of_events()

    start = time.perf_counter()
    snapshot = compute_rollup(
        events, PeriodType.MONTHLY, date(2026, 1, 1), date(2026, 1, 31), session_id=None
    )
    elapsed = time.perf_counter() - start

    assert elapsed < ROLLUP_BUDGET_SECONDS, (
        f"compute_rollup took {elapsed:.3f}s for {EVENT_COUNT} events, "
        f"exceeding the {ROLLUP_BUDGET_SECONDS:.1f}s budget"
    )
    assert snapshot.avg_focus_score is not None
    assert snapshot.raw_metrics["event_count"] == EVENT_COUNT
