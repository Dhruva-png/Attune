from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from attune.core.events.schema import Event, EventType
from attune.llm.coach import AICoach
from attune.llm.provider import LLMProviderError

T0 = datetime(2026, 1, 5, 9, 0)


def make_event(event_type: EventType, timestamp: datetime, **kwargs) -> Event:
    return Event(
        session_id=kwargs.pop("session_id", uuid4()),
        type=event_type,
        timestamp=timestamp,
        confidence=kwargs.pop("confidence", 0.9),
        source_module="test",
        **kwargs,
    )


def phone_focus_correlation_events(affected: int, unaffected: int) -> list[Event]:
    events: list[Event] = []
    for i in range(affected + unaffected):
        pickup_time = T0 + timedelta(hours=i)
        events.append(
            make_event(
                EventType.FOCUS_SCORE_UPDATED,
                pickup_time - timedelta(minutes=1),
                metadata={"score": 80.0},
            )
        )
        events.append(make_event(EventType.PHONE_PICKUP, pickup_time))
        drop = 30.0 if i < affected else 5.0  # affected: big drop; unaffected: small drop
        events.append(
            make_event(
                EventType.FOCUS_SCORE_UPDATED,
                pickup_time + timedelta(minutes=2),
                metadata={"score": 80.0 - drop},
            )
        )
    return events


def posture_deterioration_events(sessions: int, average_minutes: float) -> list[Event]:
    events: list[Event] = []
    for i in range(sessions):
        session_id = uuid4()
        start = T0 + timedelta(days=i)
        events.append(make_event(EventType.SESSION_STARTED, start, session_id=session_id))
        events.append(
            make_event(
                EventType.POOR_POSTURE,
                start + timedelta(minutes=average_minutes),
                session_id=session_id,
            )
        )
    return events


def best_hours_events() -> list[Event]:
    events = []
    for minute in range(5):
        events.append(
            make_event(
                EventType.FOCUS_SCORE_UPDATED,
                T0.replace(hour=9, minute=minute),
                metadata={"score": 90.0},
            )
        )
        events.append(
            make_event(
                EventType.FOCUS_SCORE_UPDATED,
                T0.replace(hour=14, minute=minute),
                metadata={"score": 30.0},
            )
        )
    return events


class StubLLMProvider:
    def __init__(self, response: str | None = None, error: Exception | None = None) -> None:
        self.name = "stub"
        self._response = response
        self._error = error
        self.calls: list[tuple[str, str | None]] = []

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        if self._error:
            raise self._error
        return self._response or "rephrased"


@pytest.mark.asyncio
async def test_no_events_yields_no_insights() -> None:
    coach = AICoach()
    assert await coach.generate_insights([]) == []


@pytest.mark.asyncio
async def test_phone_focus_correlation_detected_with_evidence() -> None:
    events = phone_focus_correlation_events(affected=3, unaffected=1)
    coach = AICoach()

    insights = await coach.generate_insights(events)

    phone_insight = next(i for i in insights if "phone" in i.text.lower())
    assert "3 of 4" in phone_insight.text
    assert len(phone_insight.evidence_event_ids) == 3
    assert 0.0 < phone_insight.confidence <= 0.95
    pickup_ids = {e.id for e in events if e.type == EventType.PHONE_PICKUP}
    assert set(phone_insight.evidence_event_ids).issubset(pickup_ids)


@pytest.mark.asyncio
async def test_phone_focus_correlation_suppressed_below_sample_threshold() -> None:
    events = phone_focus_correlation_events(affected=2, unaffected=0)
    coach = AICoach()

    insights = await coach.generate_insights(events)

    assert not any("phone" in i.text.lower() for i in insights)


@pytest.mark.asyncio
async def test_posture_deterioration_detected_with_evidence() -> None:
    events = posture_deterioration_events(sessions=2, average_minutes=90)
    coach = AICoach()

    insights = await coach.generate_insights(events)

    posture_insight = next(i for i in insights if "posture" in i.text.lower())
    assert "90 minutes" in posture_insight.text
    assert len(posture_insight.evidence_event_ids) == 2


@pytest.mark.asyncio
async def test_posture_deterioration_suppressed_with_single_session() -> None:
    events = posture_deterioration_events(sessions=1, average_minutes=90)
    coach = AICoach()

    insights = await coach.generate_insights(events)

    assert not any("posture" in i.text.lower() for i in insights)


@pytest.mark.asyncio
async def test_best_hours_detected() -> None:
    events = best_hours_events()
    coach = AICoach()

    insights = await coach.generate_insights(events)

    hours_insight = next(i for i in insights if "productive" in i.text.lower())
    assert "09:00" in hours_insight.text
    assert len(hours_insight.evidence_event_ids) == 5


@pytest.mark.asyncio
async def test_best_hours_suppressed_below_sample_threshold() -> None:
    events = [
        make_event(
            EventType.FOCUS_SCORE_UPDATED, T0.replace(hour=9), metadata={"score": 90.0}
        )
    ]
    coach = AICoach()

    insights = await coach.generate_insights(events)

    assert not any("productive" in i.text.lower() for i in insights)


@pytest.mark.asyncio
async def test_without_llm_provider_returns_deterministic_text() -> None:
    events = phone_focus_correlation_events(affected=3, unaffected=0)
    coach = AICoach(llm_provider=None)

    insights = await coach.generate_insights(events)

    assert insights[0].text.startswith("You consistently lose focus")


@pytest.mark.asyncio
async def test_with_llm_provider_rephrases_text_but_keeps_evidence() -> None:
    events = phone_focus_correlation_events(affected=3, unaffected=0)
    stub = StubLLMProvider(response="Phones derail your focus fast.")
    coach = AICoach(llm_provider=stub)

    insights = await coach.generate_insights(events)

    assert insights[0].text == "Phones derail your focus fast."
    assert len(insights[0].evidence_event_ids) == 3
    assert len(stub.calls) == len(insights)
    # the original computed fact must be embedded in the prompt sent to the LLM
    assert "3 of 3" in stub.calls[0][0]


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_deterministic_text() -> None:
    events = phone_focus_correlation_events(affected=3, unaffected=0)
    stub = StubLLMProvider(error=LLMProviderError("boom"))
    coach = AICoach(llm_provider=stub)

    insights = await coach.generate_insights(events)

    assert insights[0].text.startswith("You consistently lose focus")
