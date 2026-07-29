from __future__ import annotations

import pytest
from attune.vision.camera.fps_governor import FPSGovernor


def test_rejects_non_positive_target_fps() -> None:
    with pytest.raises(ValueError):
        FPSGovernor(target_fps=0)
    with pytest.raises(ValueError):
        FPSGovernor(target_fps=-5)


def test_first_frame_always_processed() -> None:
    governor = FPSGovernor(target_fps=8)
    assert governor.should_process(now=0.0) is True


def test_frame_within_interval_is_skipped() -> None:
    governor = FPSGovernor(target_fps=8)  # interval = 0.125s
    governor.should_process(now=0.0)
    assert governor.should_process(now=0.05) is False


def test_frame_after_interval_is_processed() -> None:
    governor = FPSGovernor(target_fps=8)
    governor.should_process(now=0.0)
    assert governor.should_process(now=0.2) is True


def test_reset_allows_immediate_processing_again() -> None:
    governor = FPSGovernor(target_fps=8)
    governor.should_process(now=0.0)
    governor.reset()
    assert governor.should_process(now=0.01) is True
