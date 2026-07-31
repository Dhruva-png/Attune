from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from attune.behaviour.confidence import gate
from attune.core.events.schema import Event, EventType
from attune.core.value_objects.geometry import Landmark
from attune.vision.face.signals import LEFT_EYE_INDICES, RIGHT_EYE_INDICES

FACE_REFERENCE_LANDMARK_INDEX = 4  # nose tip in the 468-point face mesh topology
GAZE_LOOKING_THRESHOLD = 0.7
CONFIRM_FRAMES = 5

WEIGHT_GAZE = 0.35
WEIGHT_POSTURE = 0.20
WEIGHT_PHONE = 0.25
WEIGHT_PRESENCE = 0.20


def _centroid(landmarks: list[Landmark], indices: tuple[int, ...]) -> tuple[float, float]:
    xs = [landmarks[i].point.x for i in indices]
    ys = [landmarks[i].point.y for i in indices]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def gaze_symmetry(face_landmarks: list[Landmark]) -> float | None:
    """Lightweight gaze-direction proxy: how symmetric the eye-to-nose
    distances are. 1.0 = looking straight ahead; lower = head turned away.
    Not true 3D head-pose estimation (that needs solvePnP + camera
    intrinsics) — a deliberately simple heuristic for a first pass.
    """
    required_max = max(*LEFT_EYE_INDICES, *RIGHT_EYE_INDICES, FACE_REFERENCE_LANDMARK_INDEX)
    if len(face_landmarks) <= required_max:
        return None

    nose = face_landmarks[FACE_REFERENCE_LANDMARK_INDEX].point
    left_x, left_y = _centroid(face_landmarks, LEFT_EYE_INDICES)
    right_x, right_y = _centroid(face_landmarks, RIGHT_EYE_INDICES)

    left_dist = math.dist((left_x, left_y), (nose.x, nose.y))
    right_dist = math.dist((right_x, right_y), (nose.x, nose.y))
    if max(left_dist, right_dist) == 0:
        return 1.0
    return min(left_dist, right_dist) / max(left_dist, right_dist)


class FocusEngine:
    """Combines gaze, posture, phone activity, and presence into a 0-100
    focus score, emitted every update as FOCUS_SCORE_UPDATED, plus debounced
    LOOKING_AT_SCREEN / LOOKED_AWAY transitions.
    """

    def __init__(
        self, confidence_threshold: float = 0.6, source_module: str = "behaviour.focus"
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._source_module = source_module
        self._is_looking: bool | None = None
        self._pending_state: bool | None = None
        self._pending_streak = 0
        self._looked_away_at: datetime | None = None

    def update(
        self,
        face_landmarks: list[Landmark],
        is_present: bool,
        posture_is_good: bool | None,
        phone_recently_active: bool,
        session_id: UUID,
        timestamp: datetime,
    ) -> list[Event]:
        gaze = gaze_symmetry(face_landmarks) if is_present else None
        gaze_factor = gaze if gaze is not None else 0.0
        presence_factor = 1.0 if is_present else 0.0
        posture_factor = 1.0 if posture_is_good else (0.5 if posture_is_good is None else 0.3)
        phone_factor = 0.3 if phone_recently_active else 1.0

        if not is_present:
            score = 0.0
            confidence = 0.8
        else:
            score = (
                gaze_factor * WEIGHT_GAZE
                + posture_factor * WEIGHT_POSTURE
                + phone_factor * WEIGHT_PHONE
                + presence_factor * WEIGHT_PRESENCE
            ) * 100.0
            confidence = 1.0 if gaze is not None else 0.5

        score_event = gate(
            Event(
                session_id=session_id,
                type=EventType.FOCUS_SCORE_UPDATED,
                timestamp=timestamp,
                confidence=confidence,
                metadata={
                    "score": score,
                    "contributing_factors": {
                        "gaze": gaze_factor,
                        "posture": posture_factor,
                        "phone": phone_factor,
                        "presence": presence_factor,
                    },
                },
                source_module=self._source_module,
            ),
            self._confidence_threshold,
        )

        is_looking = is_present and gaze_factor >= GAZE_LOOKING_THRESHOLD
        return [
            score_event,
            *self._evaluate_gaze_transition(is_looking, confidence, session_id, timestamp),
        ]

    def _evaluate_gaze_transition(
        self, is_looking: bool, confidence: float, session_id: UUID, timestamp: datetime
    ) -> list[Event]:
        if self._pending_state == is_looking:
            self._pending_streak += 1
        else:
            self._pending_state = is_looking
            self._pending_streak = 1

        if self._pending_streak < CONFIRM_FRAMES or self._is_looking == is_looking:
            return []

        self._is_looking = is_looking
        if is_looking:
            duration_ms = None
            if self._looked_away_at is not None:
                duration_ms = int((timestamp - self._looked_away_at).total_seconds() * 1000)
                self._looked_away_at = None
            event = Event(
                session_id=session_id,
                type=EventType.LOOKING_AT_SCREEN,
                timestamp=timestamp,
                confidence=confidence,
                duration_ms=duration_ms,
                source_module=self._source_module,
            )
        else:
            self._looked_away_at = timestamp
            event = Event(
                session_id=session_id,
                type=EventType.LOOKED_AWAY,
                timestamp=timestamp,
                confidence=confidence,
                source_module=self._source_module,
            )
        return [gate(event, self._confidence_threshold)]
