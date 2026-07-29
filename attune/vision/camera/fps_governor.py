from __future__ import annotations


class FPSGovernor:
    """Decides whether a captured frame should be forwarded to inference,
    decoupling the ~30 FPS capture loop from the 5-10 FPS inference target.
    """

    def __init__(self, target_fps: float) -> None:
        if target_fps <= 0:
            raise ValueError(f"target_fps must be positive, got {target_fps}")
        self._interval = 1.0 / target_fps
        self._last_processed: float | None = None

    def should_process(self, now: float) -> bool:
        if self._last_processed is None or (now - self._last_processed) >= self._interval:
            self._last_processed = now
            return True
        return False

    def reset(self) -> None:
        self._last_processed = None
