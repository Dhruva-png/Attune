from __future__ import annotations

import cv2

from attune.core.value_objects.detection import TrackedDetection
from attune.core.value_objects.geometry import Landmark
from attune.vision.camera.types import FrameArray

# RGB, not BGR — by the time a frame reaches here it's already gone through
# Preprocessor.process()'s to_rgb() step (models need RGB), so it's drawn on
# in RGB order and only flipped to BGR right before JPEG encoding. Colors
# match the dashboard's own brand palette (attune/dashboard/theme/tokens.py)
# so the live preview feels like one product, not a raw debug view.
_POSE_COLOR = (108, 92, 231)  # accent_indigo #6C5CE7
_FACE_COLOR = (0, 210, 160)  # accent_teal, kept small/dim so 468 points don't overwhelm
_HAND_COLOR = (0, 210, 160)  # accent_teal #00D2A0
_PHONE_COLOR = (255, 90, 95)  # alert #FF5A5F
_MIN_VISIBILITY = 0.5

_POSE_CONNECTIONS = (
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("nose", "left_shoulder"),
    ("nose", "right_shoulder"),
)


def _px(landmark: Landmark, width: int, height: int) -> tuple[int, int]:
    return int(landmark.point.x * width), int(landmark.point.y * height)


def draw_overlays(
    frame: FrameArray,
    *,
    pose_landmarks: list[Landmark],
    face_landmarks: list[Landmark],
    hand_landmarks: list[Landmark],
    phone_tracks: list[TrackedDetection],
) -> FrameArray:
    """Returns an annotated copy of frame — skeleton/mesh/hand points plus a
    phone bounding box — for the live dashboard preview. Purely cosmetic;
    never touches the (unannotated) frame actual inference runs against."""
    annotated = frame.copy()
    height, width = annotated.shape[:2]

    by_name = {lm.name: lm for lm in pose_landmarks if lm.visibility >= _MIN_VISIBILITY}
    for start_name, end_name in _POSE_CONNECTIONS:
        start = by_name.get(start_name)
        end = by_name.get(end_name)
        if start is not None and end is not None:
            cv2.line(annotated, _px(start, width, height), _px(end, width, height), _POSE_COLOR, 2)
    for lm in by_name.values():
        cv2.circle(annotated, _px(lm, width, height), 4, _POSE_COLOR, -1)

    for lm in face_landmarks:
        if lm.visibility >= _MIN_VISIBILITY:
            cv2.circle(annotated, _px(lm, width, height), 1, _FACE_COLOR, -1)

    for lm in hand_landmarks:
        if lm.visibility >= _MIN_VISIBILITY:
            cv2.circle(annotated, _px(lm, width, height), 3, _HAND_COLOR, -1)

    for tracked in phone_tracks:
        bbox = tracked.detection.bbox
        top_left = (int(bbox.x_min * width), int(bbox.y_min * height))
        bottom_right = (int(bbox.x_max * width), int(bbox.y_max * height))
        cv2.rectangle(annotated, top_left, bottom_right, _PHONE_COLOR, 2)
        cv2.putText(
            annotated,
            "phone",
            (top_left[0], max(top_left[1] - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            _PHONE_COLOR,
            1,
            cv2.LINE_AA,
        )

    return annotated


def encode_jpeg(frame: FrameArray, quality: int = 80) -> bytes:
    # cv2.imencode assumes BGR channel order; the frame here is RGB (see
    # draw_overlays' note above), so without this the JPEG comes out with
    # red/blue swapped.
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    ok, buffer = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("failed to encode frame as JPEG")
    return bytes(buffer)
