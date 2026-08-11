from __future__ import annotations

import pytest
from attune.core.entities.fatigue import FatigueLevel, FatigueState
from attune.core.entities.focus import FocusScore
from attune.core.entities.posture import PostureMetric


def test_fatigue_state_accepts_valid_confidence() -> None:
    state = FatigueState(level=FatigueLevel.TIRED, confidence=0.8)
    assert state.confidence == 0.8


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_fatigue_state_rejects_confidence_outside_unit_range(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence must be within"):
        FatigueState(level=FatigueLevel.NORMAL, confidence=confidence)


def test_focus_score_accepts_valid_value() -> None:
    score = FocusScore(
        value=72.5, gaze_factor=0.8, posture_factor=0.9, phone_factor=1.0, presence_factor=1.0
    )
    assert score.value == 72.5


@pytest.mark.parametrize("value", [-0.01, 100.01])
def test_focus_score_rejects_value_outside_zero_to_hundred(value: float) -> None:
    with pytest.raises(ValueError, match=r"FocusScore must be within \[0, 100\]"):
        FocusScore(
            value=value, gaze_factor=0.8, posture_factor=0.9, phone_factor=1.0, presence_factor=1.0
        )


def test_posture_metric_holds_raw_geometry_without_validation() -> None:
    metric = PostureMetric(neck_angle_deg=42.0, shoulder_delta_px=3.5, forward_lean_deg=12.0)
    assert metric.neck_angle_deg == 42.0
