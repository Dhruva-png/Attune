from __future__ import annotations

import asyncio
from typing import Any

import httpx
from PySide6.QtCore import QObject, QTimer, Signal

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.base import PollingViewModel

LIVE_STATS_POLL_INTERVAL_MS = 2000
# Much shorter than the stats cadence — a preview needs to feel live, so this
# runs on its own QTimer rather than being coupled to LIVE_STATS_POLL_INTERVAL_MS.
LIVE_FRAME_POLL_INTERVAL_MS = 300


class LiveViewModel(PollingViewModel):
    stats_updated = Signal(dict)
    stats_unavailable = Signal()
    frame_updated = Signal(bytes)
    frame_unavailable = Signal()

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(interval_ms=LIVE_STATS_POLL_INTERVAL_MS, parent=parent)
        self._api_client = api_client
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._poll_frame)

    def start(self) -> None:
        super().start()
        self._poll_frame()
        self._frame_timer.start(LIVE_FRAME_POLL_INTERVAL_MS)

    def stop(self) -> None:
        super().stop()
        self._frame_timer.stop()

    async def refresh_async(self) -> None:
        stats: dict[str, Any] | None = await self._api_client.get_live_stats()
        if stats is None:
            self.stats_unavailable.emit()
        else:
            self.stats_updated.emit(stats)

    def _poll_frame(self) -> None:
        asyncio.ensure_future(self._safe_poll_frame())

    async def _safe_poll_frame(self) -> None:
        try:
            frame = await self._api_client.get_live_frame()
        except httpx.HTTPError:
            self.frame_unavailable.emit()
            return
        if frame is None:
            self.frame_unavailable.emit()
        else:
            self.frame_updated.emit(frame)
