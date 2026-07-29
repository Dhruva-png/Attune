from __future__ import annotations

from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarkerResult

from attune.core.value_objects.geometry import Landmark, Point
from attune.vision.camera.types import FrameArray
from attune.vision.model_assets import ensure_model

POSE_LANDMARK_NAMES = [landmark.name.lower() for landmark in mp.tasks.vision.PoseLandmark]


def pose_result_to_landmarks(result: PoseLandmarkerResult) -> list[Landmark]:
    if not result.pose_landmarks:
        return []
    detected = result.pose_landmarks[0]  # nearest/primary person
    return [
        Landmark(
            name=POSE_LANDMARK_NAMES[i] if i < len(POSE_LANDMARK_NAMES) else f"landmark_{i}",
            point=Point(lm.x, lm.y, lm.z),
            visibility=lm.visibility if lm.visibility is not None else 1.0,
        )
        for i, lm in enumerate(detected)
    ]


class MediaPipePoseModel:
    """IPoseModel implementation backed by MediaPipe's PoseLandmarker Task."""

    def __init__(self, model_dir: Path, min_detection_confidence: float = 0.5) -> None:
        model_path = ensure_model("pose_landmarker_lite.task", model_dir)
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self._next_timestamp_ms = 0

    def infer(self, frame: FrameArray) -> list[Landmark]:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        timestamp_ms = self._next_timestamp_ms
        self._next_timestamp_ms += 1
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        return pose_result_to_landmarks(result)

    def close(self) -> None:
        self._landmarker.close()
