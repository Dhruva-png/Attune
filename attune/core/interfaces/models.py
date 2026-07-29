from __future__ import annotations

from typing import Protocol

from attune.core.interfaces.camera import Frame
from attune.core.value_objects.detection import Detection
from attune.core.value_objects.geometry import Landmark


class IPoseModel(Protocol):
    def infer(self, frame: Frame) -> list[Landmark]: ...


class IFaceModel(Protocol):
    def infer(self, frame: Frame) -> list[Landmark]: ...


class IHandModel(Protocol):
    def infer(self, frame: Frame) -> list[Landmark]: ...


class IObjectModel(Protocol):
    def infer(self, frame: Frame) -> list[Detection]: ...
