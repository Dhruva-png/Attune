from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

# Kept opaque (not numpy.ndarray) so core stays free of third-party dependencies;
# infrastructure implementations (attune.vision.camera) bind this to a real array type.
Frame = Any


class ICamera(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def frames(self) -> AsyncIterator[Frame]: ...

    @property
    def is_connected(self) -> bool: ...
