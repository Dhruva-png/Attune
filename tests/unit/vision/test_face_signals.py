from __future__ import annotations

from attune.core.value_objects.geometry import Landmark, Point
from attune.vision.face.signals import eye_aspect_ratio, mouth_aspect_ratio

EYE_INDICES = (0, 1, 2, 3, 4, 5)
MOUTH_INDICES = (0, 1, 2, 3)


def lm(x: float, y: float) -> Landmark:
    return Landmark(name="p", point=Point(x, y, 0.0))


def test_eye_aspect_ratio_is_higher_when_open_than_closed() -> None:
    open_eye = [
        lm(0.0, 0.0),  # p1 outer corner
        lm(0.25, 0.2),  # p2 top-near
        lm(0.75, 0.2),  # p3 top-far
        lm(1.0, 0.0),  # p4 inner corner
        lm(0.75, -0.2),  # p5 bottom-far
        lm(0.25, -0.2),  # p6 bottom-near
    ]
    closed_eye = [
        lm(0.0, 0.0),
        lm(0.25, 0.01),
        lm(0.75, 0.01),
        lm(1.0, 0.0),
        lm(0.75, -0.01),
        lm(0.25, -0.01),
    ]

    open_ratio = eye_aspect_ratio(open_eye, EYE_INDICES)
    closed_ratio = eye_aspect_ratio(closed_eye, EYE_INDICES)

    assert open_ratio > closed_ratio
    assert closed_ratio < 0.05


def test_eye_aspect_ratio_zero_when_corners_coincide() -> None:
    degenerate = [lm(0.5, 0.5)] * 6
    assert eye_aspect_ratio(degenerate, EYE_INDICES) == 0.0


def test_mouth_aspect_ratio_is_higher_when_open_than_closed() -> None:
    open_mouth = [lm(0.0, 0.0), lm(1.0, 0.0), lm(0.5, 0.3), lm(0.5, -0.3)]
    closed_mouth = [lm(0.0, 0.0), lm(1.0, 0.0), lm(0.5, 0.02), lm(0.5, -0.02)]

    assert mouth_aspect_ratio(open_mouth, MOUTH_INDICES) > mouth_aspect_ratio(
        closed_mouth, MOUTH_INDICES
    )


def test_mouth_aspect_ratio_zero_when_corners_coincide() -> None:
    degenerate = [lm(0.5, 0.5)] * 4
    assert mouth_aspect_ratio(degenerate, MOUTH_INDICES) == 0.0
