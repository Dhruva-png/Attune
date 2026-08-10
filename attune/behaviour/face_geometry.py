from __future__ import annotations

import math

from attune.core.value_objects.geometry import Landmark

# Standard 6-point eye landmark index sets in MediaPipe's 468-point face mesh
# topology, ordered [outer_corner, top_1, top_2, inner_corner, bottom_2, bottom_1]
# for the Soukupova & Cech eye-aspect-ratio formulation.
LEFT_EYE_INDICES: tuple[int, int, int, int, int, int] = (362, 385, 387, 263, 373, 380)
RIGHT_EYE_INDICES: tuple[int, int, int, int, int, int] = (33, 160, 158, 133, 153, 144)

# 4-point mouth index set: [left_corner, right_corner, top_center, bottom_center].
MOUTH_INDICES: tuple[int, int, int, int] = (61, 291, 13, 14)


def _distance(a: Landmark, b: Landmark) -> float:
    return math.dist((a.point.x, a.point.y), (b.point.x, b.point.y))


def eye_aspect_ratio(
    landmarks: list[Landmark],
    indices: tuple[int, int, int, int, int, int] = RIGHT_EYE_INDICES,
) -> float:
    p1, p2, p3, p4, p5, p6 = (landmarks[i] for i in indices)
    horizontal = _distance(p1, p4)
    if horizontal == 0:
        return 0.0
    vertical = _distance(p2, p6) + _distance(p3, p5)
    return vertical / (2.0 * horizontal)


def mouth_aspect_ratio(
    landmarks: list[Landmark], indices: tuple[int, int, int, int] = MOUTH_INDICES
) -> float:
    left, right, top, bottom = (landmarks[i] for i in indices)
    horizontal = _distance(left, right)
    if horizontal == 0:
        return 0.0
    return _distance(top, bottom) / horizontal
