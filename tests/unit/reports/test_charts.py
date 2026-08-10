from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.events.schema import Event, EventType
from attune.reports.charts import (
    daily_average_focus_figure,
    focus_score_over_time_figure,
    render_png,
)

SESSION_ID = uuid4()


def _focus_event(hour: int, minute: int, score: float) -> Event:
    return Event(
        session_id=SESSION_ID,
        type=EventType.FOCUS_SCORE_UPDATED,
        timestamp=datetime(2026, 1, 5, hour, minute),
        confidence=0.9,
        metadata={"score": score},
        source_module="test",
    )


def _snapshot(avg_focus_score: float | None) -> AnalyticsSnapshot:
    return AnalyticsSnapshot(
        period_type=PeriodType.DAILY,
        period_start=date(2026, 1, 5),
        period_end=date(2026, 1, 5),
        avg_focus_score=avg_focus_score,
    )


def test_focus_score_over_time_figure_returns_none_when_no_focus_events() -> None:
    other_event = Event(
        session_id=SESSION_ID,
        type=EventType.YAWN,
        timestamp=datetime(2026, 1, 5, 9, 0),
        confidence=0.9,
        source_module="test",
    )
    assert focus_score_over_time_figure([other_event]) is None


def test_focus_score_over_time_figure_plots_sorted_points() -> None:
    events = [_focus_event(9, 30, 70.0), _focus_event(9, 0, 50.0)]
    fig = focus_score_over_time_figure(events)

    assert fig is not None
    trace = fig.data[0]
    assert list(trace.y) == [50.0, 70.0]


def test_daily_average_focus_figure_returns_none_when_all_scores_missing() -> None:
    daily_snapshots = [(date(2026, 1, 5), _snapshot(None))]
    assert daily_average_focus_figure(daily_snapshots) is None


def test_daily_average_focus_figure_skips_days_without_data() -> None:
    daily_snapshots = [
        (date(2026, 1, 5), _snapshot(80.0)),
        (date(2026, 1, 6), _snapshot(None)),
    ]
    fig = daily_average_focus_figure(daily_snapshots)

    assert fig is not None
    trace = fig.data[0]
    assert list(trace.y) == [80.0]


def test_render_png_produces_nonempty_bytes() -> None:
    fig = focus_score_over_time_figure([_focus_event(9, 0, 60.0), _focus_event(9, 1, 65.0)])
    assert fig is not None

    png_bytes = render_png(fig)

    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG")
