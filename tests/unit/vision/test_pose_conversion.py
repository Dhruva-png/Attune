from __future__ import annotations

from attune.vision.pose.model import POSE_LANDMARK_NAMES, pose_result_to_landmarks
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarkerResult


def make_landmark(x: float, y: float, z: float, visibility: float | None) -> NormalizedLandmark:
    return NormalizedLandmark(x=x, y=y, z=z, visibility=visibility, presence=visibility)


def test_empty_result_yields_no_landmarks() -> None:
    result = PoseLandmarkerResult(pose_landmarks=[], pose_world_landmarks=[])
    assert pose_result_to_landmarks(result) == []


def test_converts_all_33_named_pose_landmarks() -> None:
    detected = [make_landmark(i * 0.01, i * 0.02, i * 0.03, 0.9) for i in range(33)]
    result = PoseLandmarkerResult(pose_landmarks=[detected], pose_world_landmarks=[])

    landmarks = pose_result_to_landmarks(result)

    assert len(landmarks) == 33
    assert [lm.name for lm in landmarks] == POSE_LANDMARK_NAMES
    assert landmarks[0].point.x == 0.0
    assert landmarks[5].point.y == 5 * 0.02
    assert landmarks[5].visibility == 0.9


def test_missing_visibility_defaults_to_fully_visible() -> None:
    detected = [make_landmark(0.0, 0.0, 0.0, None)]
    result = PoseLandmarkerResult(pose_landmarks=[detected], pose_world_landmarks=[])

    landmarks = pose_result_to_landmarks(result)

    assert landmarks[0].visibility == 1.0


def test_only_primary_person_is_converted() -> None:
    person_a = [make_landmark(0.1, 0.1, 0.1, 0.9) for _ in range(33)]
    person_b = [make_landmark(0.9, 0.9, 0.9, 0.9) for _ in range(33)]
    result = PoseLandmarkerResult(pose_landmarks=[person_a, person_b], pose_world_landmarks=[])

    landmarks = pose_result_to_landmarks(result)

    assert len(landmarks) == 33
    assert landmarks[0].point.x == 0.1
