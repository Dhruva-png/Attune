from __future__ import annotations

from attune.core.events.schema import Event, EventType


def gate(event: Event, threshold: float) -> Event:
    """Suppresses a candidate event below the confidence threshold.

    Per docs/architecture/05-event-schema.md: low confidence suppresses
    conclusions rather than silently dropping them — the original type and
    confidence are preserved in a LOW_CONFIDENCE_SUPPRESSED event so the
    suppression itself stays auditable.
    """
    if event.confidence >= threshold:
        return event
    return Event(
        session_id=event.session_id,
        type=EventType.LOW_CONFIDENCE_SUPPRESSED,
        confidence=event.confidence,
        metadata={
            "original_type": event.type.value,
            "original_confidence": event.confidence,
            "threshold": threshold,
        },
        source_module=event.source_module,
    )
