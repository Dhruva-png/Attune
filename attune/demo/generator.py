from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from attune.behaviour.phone.engine import classify_interaction
from attune.core.entities.session import Session, SessionStatus
from attune.core.events.schema import Event, EventType
from attune.demo.scenarios import DEFAULT_WEEK_PLAN, Scenario

# A synthetic tick every 60s is plenty for a smooth trend chart without
# generating tens of thousands of events per session the way the real
# ~8fps vision pipeline would.
FOCUS_TICK_SECONDS = 60
SESSION_DURATION_RANGE_MINUTES = (90, 180)
SESSION_START_HOUR_RANGE = (8, 10)
SOURCE_MODULE = "demo"


@dataclass(frozen=True, slots=True)
class GeneratedSession:
    session: Session
    events: list[Event]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _generate_focus_events(
    scenario: Scenario,
    session_id: UUID,
    start_at: datetime,
    duration: timedelta,
    rng: random.Random,
) -> list[Event]:
    events = []
    elapsed = timedelta(0)
    while elapsed < duration:
        elapsed_hours = elapsed.total_seconds() / 3600
        score = _clamp(
            scenario.focus_baseline
            + scenario.focus_trend_per_hour * elapsed_hours
            + rng.gauss(0, scenario.focus_volatility)
        )
        events.append(
            Event(
                session_id=session_id,
                type=EventType.FOCUS_SCORE_UPDATED,
                timestamp=start_at + elapsed,
                confidence=rng.uniform(0.75, 0.98),
                metadata={"score": round(score, 1)},
                source_module=SOURCE_MODULE,
            )
        )
        elapsed += timedelta(seconds=FOCUS_TICK_SECONDS)
    return events


def _generate_posture_events(
    scenario: Scenario,
    session_id: UUID,
    start_at: datetime,
    duration: timedelta,
    rng: random.Random,
) -> list[Event]:
    total_seconds = duration.total_seconds()
    num_segments = rng.randint(3, 7)
    breakpoints = sorted(rng.uniform(0, total_seconds) for _ in range(num_segments - 1))

    events = []
    for segment_start in (0.0, *breakpoints):
        is_good = rng.random() < scenario.posture_good_ratio
        events.append(
            Event(
                session_id=session_id,
                type=EventType.GOOD_POSTURE if is_good else EventType.POOR_POSTURE,
                timestamp=start_at + timedelta(seconds=segment_start),
                confidence=rng.uniform(0.8, 0.97),
                source_module=SOURCE_MODULE,
            )
        )
    return events


def _generate_phone_events(
    scenario: Scenario,
    session_id: UUID,
    start_at: datetime,
    duration: timedelta,
    rng: random.Random,
) -> list[Event]:
    total_seconds = duration.total_seconds()
    if total_seconds <= 120:
        return []

    hours = total_seconds / 3600
    count = max(0, round(rng.gauss(scenario.phone_pickups_per_hour * hours, 1.0)))
    offsets = sorted(rng.uniform(60, total_seconds - 60) for _ in range(count))

    events = []
    for offset in offsets:
        pickup_at = start_at + timedelta(seconds=offset)
        interaction_seconds = rng.uniform(*scenario.phone_pickup_duration_range_s)
        down_at = pickup_at + timedelta(seconds=interaction_seconds)
        events.append(
            Event(
                session_id=session_id,
                type=EventType.PHONE_PICKUP,
                timestamp=pickup_at,
                confidence=rng.uniform(0.7, 0.95),
                source_module=SOURCE_MODULE,
            )
        )
        events.append(
            Event(
                session_id=session_id,
                type=EventType.PHONE_DOWN,
                timestamp=down_at,
                confidence=0.9,
                duration_ms=int(interaction_seconds * 1000),
                metadata={"interaction_class": classify_interaction(interaction_seconds)},
                source_module=SOURCE_MODULE,
            )
        )
    return events


def _generate_fatigue_events(
    scenario: Scenario,
    session_id: UUID,
    start_at: datetime,
    duration: timedelta,
    rng: random.Random,
) -> list[Event]:
    total_seconds = duration.total_seconds()
    hours = total_seconds / 3600
    events: list[Event] = []

    for event_type, rate in (
        (EventType.YAWN, scenario.yawns_per_hour),
        (EventType.LONG_BLINK, scenario.long_blinks_per_hour),
        (EventType.FACE_TOUCH, scenario.face_touches_per_hour),
    ):
        expected = rate * hours
        count = max(0, round(rng.gauss(expected, max(expected * 0.3, 0.5))))
        for _ in range(count):
            offset = rng.uniform(0, total_seconds)
            timestamp = start_at + timedelta(seconds=offset)
            confidence = rng.uniform(0.7, 0.95)
            if event_type == EventType.YAWN:
                events.append(
                    Event(
                        session_id=session_id,
                        type=event_type,
                        timestamp=timestamp,
                        confidence=confidence,
                        metadata={"mouth_aspect_ratio": round(rng.uniform(0.5, 0.9), 2)},
                        source_module=SOURCE_MODULE,
                    )
                )
            elif event_type == EventType.LONG_BLINK:
                events.append(
                    Event(
                        session_id=session_id,
                        type=event_type,
                        timestamp=timestamp,
                        confidence=confidence,
                        duration_ms=rng.randint(400, 900),
                        source_module=SOURCE_MODULE,
                    )
                )
            else:
                events.append(
                    Event(
                        session_id=session_id,
                        type=event_type,
                        timestamp=timestamp,
                        confidence=confidence,
                        source_module=SOURCE_MODULE,
                    )
                )

    levels = scenario.fatigue_progression
    if len(levels) > 1:
        step = total_seconds / len(levels)
        for i in range(1, len(levels)):
            events.append(
                Event(
                    session_id=session_id,
                    type=EventType.FATIGUE_LEVEL_CHANGED,
                    timestamp=start_at + timedelta(seconds=step * i),
                    confidence=rng.uniform(0.75, 0.95),
                    metadata={
                        "from_level": levels[i - 1].value,
                        "to_level": levels[i].value,
                        "contributing_signals": [],
                        "blink_rate_per_minute": round(rng.uniform(8, 25), 1),
                    },
                    source_module=SOURCE_MODULE,
                )
            )
    return events


def _generate_break_events(
    scenario: Scenario,
    session_id: UUID,
    start_at: datetime,
    duration: timedelta,
    rng: random.Random,
) -> list[Event]:
    total_seconds = duration.total_seconds()
    if total_seconds < 600:
        return []

    events = []
    for _ in range(rng.randint(*scenario.break_count_range)):
        break_seconds = rng.uniform(*scenario.break_duration_range_s)
        latest_start = total_seconds - break_seconds - 60
        if latest_start <= 60:
            continue
        offset = rng.uniform(60, latest_start)
        left_at = start_at + timedelta(seconds=offset)
        returned_at = left_at + timedelta(seconds=break_seconds)
        events.append(
            Event(
                session_id=session_id,
                type=EventType.LEFT_DESK,
                timestamp=left_at,
                confidence=rng.uniform(0.8, 0.95),
                source_module=SOURCE_MODULE,
            )
        )
        events.append(
            Event(
                session_id=session_id,
                type=EventType.RETURNED,
                timestamp=returned_at,
                confidence=rng.uniform(0.8, 0.95),
                duration_ms=int(break_seconds * 1000),
                source_module=SOURCE_MODULE,
            )
        )
    return events


def generate_session(
    scenario: Scenario,
    start_at: datetime,
    duration_minutes: int,
    rng: random.Random,
) -> GeneratedSession:
    session_id = uuid4()
    duration = timedelta(minutes=duration_minutes)
    end_at = start_at + duration

    focus_events = _generate_focus_events(scenario, session_id, start_at, duration, rng)

    events: list[Event] = [
        Event(
            session_id=session_id,
            type=EventType.SESSION_STARTED,
            timestamp=start_at,
            confidence=1.0,
            source_module=SOURCE_MODULE,
        ),
        *focus_events,
        *_generate_posture_events(scenario, session_id, start_at, duration, rng),
        *_generate_phone_events(scenario, session_id, start_at, duration, rng),
        *_generate_fatigue_events(scenario, session_id, start_at, duration, rng),
        *_generate_break_events(scenario, session_id, start_at, duration, rng),
        Event(
            session_id=session_id,
            type=EventType.SESSION_ENDED,
            timestamp=end_at,
            confidence=1.0,
            source_module=SOURCE_MODULE,
        ),
    ]
    events.sort(key=lambda event: event.timestamp)

    scores = [event.metadata["score"] for event in focus_events]
    avg_focus = round(sum(scores) / len(scores), 1) if scores else None

    session = Session(
        id=session_id,
        started_at=start_at,
        ended_at=end_at,
        status=SessionStatus.COMPLETED,
        focus_score_avg=avg_focus,
        posture_score_avg=round(scenario.posture_good_ratio * 100, 1),
        fatigue_level_end=scenario.fatigue_progression[-1],
    )
    return GeneratedSession(session=session, events=events)


def generate_week(
    start_date: date,
    week_plan: tuple[Scenario | None, ...] = DEFAULT_WEEK_PLAN,
    seed: int | None = None,
) -> list[GeneratedSession]:
    """Generates up to len(week_plan) sessions, one per day starting at
    start_date, skipping days where week_plan has None (e.g. weekends).
    """
    rng = random.Random(seed)
    generated: list[GeneratedSession] = []
    for offset, scenario in enumerate(week_plan):
        if scenario is None:
            continue
        day = start_date + timedelta(days=offset)
        start_hour = rng.randint(*SESSION_START_HOUR_RANGE)
        start_minute = rng.choice([0, 15, 30, 45])
        start_at = datetime.combine(day, datetime.min.time()) + timedelta(
            hours=start_hour, minutes=start_minute
        )
        duration_minutes = rng.randint(*SESSION_DURATION_RANGE_MINUTES)
        generated.append(generate_session(scenario, start_at, duration_minutes, rng))
    return generated
