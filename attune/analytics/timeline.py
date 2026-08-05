from __future__ import annotations

from dataclasses import dataclass

from attune.core.events.schema import Event, EventType

EVENT_LABELS: dict[EventType, str] = {
    EventType.SESSION_STARTED: "Started",
    EventType.SESSION_ENDED: "Ended",
    EventType.SESSION_PAUSED: "Paused",
    EventType.SESSION_RESUMED: "Resumed",
    EventType.LOOKING_AT_SCREEN: "Looking at Screen",
    EventType.LOOKED_AWAY: "Looked Away",
    EventType.PHONE_DETECTED: "Phone Detected",
    EventType.PHONE_PICKUP: "Phone Pickup",
    EventType.PHONE_DOWN: "Phone Down",
    EventType.GOOD_POSTURE: "Good Posture",
    EventType.POOR_POSTURE: "Poor Posture",
    EventType.SLUMP_STARTED: "Slump Started",
    EventType.SLUMP_ENDED: "Slump Ended",
    EventType.YAWN: "Yawn",
    EventType.LONG_BLINK: "Long Blink",
    EventType.FACE_TOUCH: "Face Touch",
    EventType.FATIGUE_LEVEL_CHANGED: "Fatigue Level Changed",
    EventType.LEFT_DESK: "Left Desk",
    EventType.RETURNED: "Returned",
    EventType.COFFEE_DRINK: "Coffee",
    EventType.CAMERA_DISCONNECTED: "Camera Disconnected",
    EventType.CAMERA_RECONNECTED: "Camera Reconnected",
}

# FOCUS_SCORE_UPDATED fires continuously and LOW_CONFIDENCE_SUPPRESSED is
# noise, not a user-facing moment — both excluded from the default timeline
# (see the example timeline in docs/architecture spec: discrete moments only).
DEFAULT_TIMELINE_EVENT_TYPES = frozenset(EVENT_LABELS)


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    time: str
    label: str
    event_type: EventType
    confidence: float


def build_timeline(
    events: list[Event], *, include_types: frozenset[EventType] | None = None
) -> list[TimelineEntry]:
    allowed = include_types if include_types is not None else DEFAULT_TIMELINE_EVENT_TYPES
    ordered = sorted((e for e in events if e.type in allowed), key=lambda e: e.timestamp)
    return [
        TimelineEntry(
            time=e.timestamp.strftime("%H:%M"),
            label=EVENT_LABELS.get(e.type, e.type.value.replace("_", " ").title()),
            event_type=e.type,
            confidence=e.confidence,
        )
        for e in ordered
    ]
