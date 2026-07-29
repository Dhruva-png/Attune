from __future__ import annotations

from attune.vision.hands.model import HAND_LANDMARK_NAMES, hand_result_to_landmarks
from mediapipe.tasks.python.components.containers.category import Category
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark
from mediapipe.tasks.python.vision.hand_landmarker import HandLandmarkerResult


def make_landmark(
    x: float, y: float, z: float, visibility: float | None = 0.9
) -> NormalizedLandmark:
    return NormalizedLandmark(x=x, y=y, z=z, visibility=visibility, presence=visibility)


def make_category(name: str) -> Category:
    return Category(index=0, score=0.95, display_name=name, category_name=name)


def test_no_hands_detected_yields_empty_list() -> None:
    result = HandLandmarkerResult(handedness=[], hand_landmarks=[], hand_world_landmarks=[])
    assert hand_result_to_landmarks(result) == []


def test_single_hand_landmarks_are_prefixed_with_handedness() -> None:
    hand = [make_landmark(i * 0.01, i * 0.01, 0.0) for i in range(21)]
    result = HandLandmarkerResult(
        handedness=[[make_category("Left")]],
        hand_landmarks=[hand],
        hand_world_landmarks=[],
    )

    landmarks = hand_result_to_landmarks(result)

    assert len(landmarks) == 21
    assert landmarks[0].name == "left_wrist"
    assert landmarks[4].name == "left_thumb_tip"
    assert [lm.name.removeprefix("left_") for lm in landmarks] == HAND_LANDMARK_NAMES


def test_two_hands_are_both_converted_and_distinguishable() -> None:
    left_hand = [make_landmark(0.1, 0.1, 0.0) for _ in range(21)]
    right_hand = [make_landmark(0.9, 0.9, 0.0) for _ in range(21)]
    result = HandLandmarkerResult(
        handedness=[[make_category("Left")], [make_category("Right")]],
        hand_landmarks=[left_hand, right_hand],
        hand_world_landmarks=[],
    )

    landmarks = hand_result_to_landmarks(result)

    assert len(landmarks) == 42
    names = {lm.name for lm in landmarks}
    assert "left_wrist" in names
    assert "right_wrist" in names
