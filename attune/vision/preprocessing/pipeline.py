from __future__ import annotations

from dataclasses import dataclass

from attune.vision.camera.types import FrameArray
from attune.vision.preprocessing.transforms import resize, to_rgb


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:
    target_width: int = 640
    target_height: int = 480
    convert_to_rgb: bool = True


class Preprocessor:
    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self._config = config or PreprocessingConfig()

    def process(self, frame: FrameArray) -> FrameArray:
        processed = resize(frame, self._config.target_width, self._config.target_height)
        if self._config.convert_to_rgb:
            processed = to_rgb(processed)
        return processed
