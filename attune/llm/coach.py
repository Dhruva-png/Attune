from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, pstdev
from uuid import UUID

from attune.analytics.trends import best_and_worst_hours
from attune.core.events.schema import Event, EventType
from attune.core.interfaces.llm import ILLMProvider
from attune.llm.provider import LLMProviderError

MIN_PHONE_SAMPLE_SIZE = 3
PHONE_FOCUS_WINDOW_MINUTES = 5
PHONE_FOCUS_DROP_THRESHOLD = 15.0

MIN_POSTURE_SAMPLE_SIZE = 2

MIN_HOURS_SAMPLE_SIZE = 3

RESPHRASE_SYSTEM_PROMPT = "You are a concise, factual productivity coach."


@dataclass(frozen=True, slots=True)
class CoachInsight:
    text: str
    confidence: float
    evidence_event_ids: tuple[UUID, ...]


def _detect_phone_focus_correlation(events: list[Event]) -> CoachInsight | None:
    """Every prediction must include confidence, every conclusion must
    reference evidence (docs/architecture spec) — so confidence and evidence
    here are computed from the actual matched events, never asserted.
    """
    pickups = sorted(
        (e for e in events if e.type == EventType.PHONE_PICKUP), key=lambda e: e.timestamp
    )
    focus_events = sorted(
        (e for e in events if e.type == EventType.FOCUS_SCORE_UPDATED and "score" in e.metadata),
        key=lambda e: e.timestamp,
    )
    if len(pickups) < MIN_PHONE_SAMPLE_SIZE or not focus_events:
        return None

    affected_count = 0
    evidence: list[UUID] = []
    for pickup in pickups:
        before = [e for e in focus_events if e.timestamp <= pickup.timestamp]
        window_end = pickup.timestamp + timedelta(minutes=PHONE_FOCUS_WINDOW_MINUTES)
        after = [e for e in focus_events if pickup.timestamp < e.timestamp <= window_end]
        if not before or not after:
            continue
        score_before = before[-1].metadata["score"]
        score_after = min(e.metadata["score"] for e in after)
        if score_before - score_after >= PHONE_FOCUS_DROP_THRESHOLD:
            affected_count += 1
            evidence.append(pickup.id)

    if affected_count < MIN_PHONE_SAMPLE_SIZE:
        return None

    ratio = affected_count / len(pickups)
    confidence = min(0.5 + ratio * 0.5, 0.95)
    text = (
        f"You consistently lose focus within {PHONE_FOCUS_WINDOW_MINUTES} minutes of checking "
        f"your phone — this happened in {affected_count} of {len(pickups)} tracked pickups."
    )
    return CoachInsight(text=text, confidence=confidence, evidence_event_ids=tuple(evidence))


def _detect_posture_deterioration_timing(events: list[Event]) -> CoachInsight | None:
    session_starts: dict[UUID, datetime] = {
        e.session_id: e.timestamp for e in events if e.type == EventType.SESSION_STARTED
    }
    if not session_starts:
        return None

    elapsed_minutes: list[float] = []
    evidence: list[UUID] = []
    for event in events:
        if event.type not in (EventType.POOR_POSTURE, EventType.SLUMP_STARTED):
            continue
        start = session_starts.get(event.session_id)
        if start is None or event.timestamp <= start:
            continue
        elapsed_minutes.append((event.timestamp - start).total_seconds() / 60)
        evidence.append(event.id)

    if len(elapsed_minutes) < MIN_POSTURE_SAMPLE_SIZE:
        return None

    average_minutes = mean(elapsed_minutes)
    spread = pstdev(elapsed_minutes) if len(elapsed_minutes) > 1 else 0.0
    consistency = max(0.0, 1 - (spread / average_minutes)) if average_minutes else 0.0
    confidence = min(0.4 + consistency * 0.5, 0.9)

    text = (
        f"Your posture tends to deteriorate after approximately {average_minutes:.0f} minutes, "
        f"based on {len(elapsed_minutes)} tracked occurrences."
    )
    return CoachInsight(text=text, confidence=confidence, evidence_event_ids=tuple(evidence))


def _detect_best_hours(events: list[Event]) -> CoachInsight | None:
    best, _worst = best_and_worst_hours(events)
    if not best:
        return None

    best_range = best[0]
    start_hour = int(best_range.split(":")[0])
    evidence = tuple(
        e.id
        for e in events
        if e.type == EventType.FOCUS_SCORE_UPDATED
        and "score" in e.metadata
        and e.timestamp.hour == start_hour
    )
    if len(evidence) < MIN_HOURS_SAMPLE_SIZE:
        return None

    confidence = min(0.5 + 0.05 * len(evidence), 0.9)
    text = f"You are most productive between {best_range}."
    return CoachInsight(text=text, confidence=confidence, evidence_event_ids=evidence)


_DETECTORS = (
    _detect_phone_focus_correlation,
    _detect_posture_deterioration_timing,
    _detect_best_hours,
)


class AICoach:
    """Reasons over collected events into evidence-backed insights.

    Confidence and evidence_event_ids always come from the deterministic
    detectors above — never from the LLM. When an ILLMProvider is configured
    it only rephrases an already-verified fact into more natural prose (with
    an explicit instruction not to add claims), and any failure there falls
    back to the plain templated text — the coach still works with no LLM
    configured at all, per the spec's graceful-degradation requirement.
    """

    def __init__(self, llm_provider: ILLMProvider | None = None) -> None:
        self._llm_provider = llm_provider

    @property
    def generated_by(self) -> str:
        return self._llm_provider.name if self._llm_provider is not None else "deterministic"

    async def generate_insights(self, events: list[Event]) -> list[CoachInsight]:
        insights = [insight for detector in _DETECTORS if (insight := detector(events)) is not None]
        if self._llm_provider is None:
            return insights

        rephrased: list[CoachInsight] = []
        for insight in insights:
            text = await self._rephrase(insight.text)
            rephrased.append(
                CoachInsight(
                    text=text,
                    confidence=insight.confidence,
                    evidence_event_ids=insight.evidence_event_ids,
                )
            )
        return rephrased

    async def _rephrase(self, fact: str) -> str:
        assert self._llm_provider is not None
        prompt = (
            "Rewrite the following productivity observation as one natural, concise sentence. "
            "State only the fact given — do not add numbers, claims, or advice not present in "
            f"it.\n\nObservation: {fact}"
        )
        try:
            return await self._llm_provider.complete(prompt, system=RESPHRASE_SYSTEM_PROMPT)
        except LLMProviderError:
            return fact
