from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field

Confidence01 = Annotated[float, Field(ge=0.0, le=1.0)]


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
    confidence: Confidence01
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_module: str

    model_config = {"frozen": True}
