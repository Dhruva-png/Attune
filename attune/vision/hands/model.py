from __future__ import annotations

from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python.vision.hand_landmarker import HandLandmarkerResult

from attune.core.value_objects.geometry import Landmark, Point
from attune.vision.camera.types import FrameArray
from attune.vision.model_assets import ensure_model

# MediaPipe Tasks has no HandLandmark enum (unlike PoseLandmark); this ordering
# is the stable, documented 21-point hand topology.
HAND_LANDMARK_NAMES = [
    "wrist",
    "thumb_cmc",
    "thumb_mcp",
    "thumb_ip",
    "thumb_tip",
    "index_finger_mcp",
    "index_finger_pip",
    "index_finger_dip",
    "index_finger_tip",
    "middle_finger_mcp",
    "middle_finger_pip",
    "middle_finger_dip",
    "middle_finger_tip",
    "ring_finger_mcp",
    "ring_finger_pip",
    "ring_finger_dip",
    "ring_finger_tip",
    "pinky_mcp",
    "pinky_pip",
    "pinky_dip",
    "pinky_tip",
]


def hand_result_to_landmarks(result: HandLandmarkerResult) -> list[Landmark]:
    landmarks: list[Landmark] = []
    for hand_index, hand_landmarks in enumerate(result.hand_landmarks):
        handedness = result.handedness[hand_index][0].category_name or "unknown"
        prefix = handedness.lower()
        for i, lm in enumerate(hand_landmarks):
            name = HAND_LANDMARK_NAMES[i] if i < len(HAND_LANDMARK_NAMES) else f"landmark_{i}"
            landmarks.append(
                Landmark(
                    name=f"{prefix}_{name}",
                    point=Point(lm.x, lm.y, lm.z),
                    visibility=lm.visibility if lm.visibility is not None else 1.0,
                )
            )
    return landmarks


class MediaPipeHandModel:
    """IHandModel implementation backed by MediaPipe's HandLandmarker Task."""

    def __init__(
        self, model_dir: Path, num_hands: int = 2, min_detection_confidence: float = 0.5
    ) -> None:
        model_path = ensure_model("hand_landmarker.task", model_dir)
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._next_timestamp_ms = 0

    def infer(self, frame: FrameArray) -> list[Landmark]:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        timestamp_ms = self._next_timestamp_ms
        self._next_timestamp_ms += 1
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        return hand_result_to_landmarks(result)

    def close(self) -> None:
        self._landmarker.close()
