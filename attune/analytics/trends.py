from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean

from attune.core.events.schema import Event, EventType


def focus_trend(events: list[Event]) -> list[tuple[datetime, float]]:
    return [
        (e.timestamp, e.metadata["score"])
        for e in sorted(events, key=lambda e: e.timestamp)
        if e.type == EventType.FOCUS_SCORE_UPDATED and "score" in e.metadata
    ]


def posture_trend(events: list[Event]) -> list[tuple[datetime, str]]:
    return [
        (e.timestamp, "good" if e.type == EventType.GOOD_POSTURE else "poor")
        for e in sorted(events, key=lambda e: e.timestamp)
        if e.type in (EventType.GOOD_POSTURE, EventType.POOR_POSTURE)
    ]


def _format_hour_range(hour: int) -> str:
    return f"{hour:02d}:00-{(hour + 1) % 24:02d}:00"


def best_and_worst_hours(events: list[Event], top_n: int = 1) -> tuple[list[str], list[str]]:
    """Buckets FOCUS_SCORE_UPDATED events by hour-of-day and returns the
    top_n highest- and lowest-average-focus hour ranges.
    """
    buckets: dict[int, list[float]] = defaultdict(list)
    for event in events:
        if event.type == EventType.FOCUS_SCORE_UPDATED and "score" in event.metadata:
            buckets[event.timestamp.hour].append(event.metadata["score"])

    if not buckets:
        return [], []

    ranked = sorted(
        ((hour, mean(scores)) for hour, scores in buckets.items()),
        key=lambda item: item[1],
        reverse=True,
    )

    best = [_format_hour_range(hour) for hour, _ in ranked[:top_n]]
    worst = [_format_hour_range(hour) for hour, _ in ranked[-top_n:]] if len(ranked) > top_n else []
    return best, worst
