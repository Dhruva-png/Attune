# Event Schema

The `Event` is Attune's universal currency — every module communicates exclusively by publishing
and subscribing to these objects on the `core.events.EventBus`.

## Base schema (Pydantic)

```python
# attune/core/events/schema.py
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field, confloat
import uuid


class EventType(StrEnum):
    # Session lifecycle
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"

    # Attention
    LOOKING_AT_SCREEN = "looking_at_screen"
    LOOKED_AWAY = "looked_away"

    # Phone
    PHONE_DETECTED = "phone_detected"
    PHONE_PICKUP = "phone_pickup"
    PHONE_DOWN = "phone_down"

    # Posture
    GOOD_POSTURE = "good_posture"
    POOR_POSTURE = "poor_posture"
    SLUMP_STARTED = "slump_started"
    SLUMP_ENDED = "slump_ended"

    # Fatigue
    YAWN = "yawn"
    LONG_BLINK = "long_blink"
    FACE_TOUCH = "face_touch"
    FATIGUE_LEVEL_CHANGED = "fatigue_level_changed"

    # Breaks / presence
    LEFT_DESK = "left_desk"
    RETURNED = "returned"
    COFFEE_DRINK = "coffee_drink"

    # Derived / continuous
    FOCUS_SCORE_UPDATED = "focus_score_updated"

    # System
    CAMERA_DISCONNECTED = "camera_disconnected"
    CAMERA_RECONNECTED = "camera_reconnected"
    LOW_CONFIDENCE_SUPPRESSED = "low_confidence_suppressed"


class Event(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: confloat(ge=0.0, le=1.0)
    duration_ms: int | None = None          # set for interval events (e.g. SLUMP_STARTED->ENDED)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_module: str                       # e.g. "vision.pose", "behaviour.posture"

    model_config = {"frozen": True}          # events are immutable once published
```

## Per-event metadata conventions

Metadata is intentionally free-form JSON, but each event type has a documented, stable shape so
downstream consumers (Analytics Engine, AI Coach, dashboard) can rely on fields existing:

| Event | `metadata` fields | `duration_ms` |
|---|---|---|
| `PHONE_PICKUP` / `PHONE_DOWN` | `bbox`, `hand_distance_px` | — |
| `PHONE_DOWN` (summary) | `interaction_class: "glance" \| "short" \| "extended"` | set (pickup→down span) |
| `LOOKED_AWAY` | `gaze_direction`, `head_yaw_deg` | set on `LOOKING_AT_SCREEN` that follows |
| `POOR_POSTURE` / `SLUMP_STARTED` | `neck_angle_deg`, `shoulder_delta_px`, `forward_lean_deg` | set on `*_ENDED` |
| `YAWN` | `mouth_aspect_ratio` | set |
| `LONG_BLINK` | `eye_aspect_ratio`, `blink_duration_ms` | set |
| `FATIGUE_LEVEL_CHANGED` | `from_level`, `to_level`, `contributing_signals: [...]` | — |
| `LEFT_DESK` / `RETURNED` | `last_seen_bbox_center` | set on `RETURNED` |
| `FOCUS_SCORE_UPDATED` | `score: 0-100`, `contributing_factors: {gaze: float, posture: float, phone: float, presence: float}` | — |
| `LOW_CONFIDENCE_SUPPRESSED` | `original_type`, `original_confidence`, `threshold` | — |

## Confidence & suppression rule

Every detector attaches a `confidence` in `[0, 1]` reflecting model certainty for that inference
(landmark visibility, detection score, temporal consistency). The shared
`behaviour/confidence.py` gate:

```python
if event.confidence < settings.performance.confidence_threshold:
    bus.publish(Event(type=EventType.LOW_CONFIDENCE_SUPPRESSED, ...))
    return  # original event is NOT published downstream
```

This guarantees the spec's rule that "low confidence suppresses conclusions" — the Analytics
Engine and AI Coach only ever see events that already cleared the bar, and the suppressed-event
trail remains auditable for debugging/QA without polluting user-facing analytics.

## Interval events

Some behaviours are naturally intervals (a slump, a phone interaction, an absence). Rather than a
separate "interval" type, Attune uses a **paired start/end event** convention:
`SLUMP_STARTED → SLUMP_ENDED`, `LEFT_DESK → RETURNED`, `PHONE_PICKUP → PHONE_DOWN`. The `_ENDED`/
terminal event carries `duration_ms` computed from the matching start event, which detectors track
via a small in-memory "open intervals" map keyed by event type. This keeps `Event` itself a flat,
simple, immutable record (good for storage and serialization) while still supporting duration
analytics.

## Transport

- **In-process**: `EventBus.publish(event)` fans out synchronously to registered `async`
  subscribers (each awaited via `asyncio.gather`, isolated with try/except so one subscriber's
  exception cannot break others).
- **Over the wire** (API → dashboard, or future remote clients): events are pushed on a
  `/live-stats` WebSocket as JSON (`Event.model_dump_json()`), so the wire format is identical to
  the in-process Pydantic model — no separate DTO layer needed.
- **At rest**: `database.repositories.EventRepository` persists every published event (post
  confidence-gate) to the `events` table, `metadata` stored as the JSON column.
