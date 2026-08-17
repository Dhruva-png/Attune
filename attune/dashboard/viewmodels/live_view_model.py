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
# ~20fps: the backend now tracks the camera's own capture rate (see
# LiveSessionManager.store_preview_frame) rather than the much slower
# inference rate, so polling can be this fast without just re-fetching the
# same stale frame.
LIVE_FRAME_POLL_INTERVAL_MS = 50


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
        self._frame_poll_in_flight = False

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
        # At a 50ms tick, a slow request could still be in flight when the
        # next timeout fires; without this guard the responses could arrive
        # out of order and briefly show a stale frame after a newer one.
        if self._frame_poll_in_flight:
            return
        self._frame_poll_in_flight = True
        asyncio.ensure_future(self._safe_poll_frame())

    async def _safe_poll_frame(self) -> None:
        try:
            frame = await self._api_client.get_live_frame()
        except httpx.HTTPError:
            self.frame_unavailable.emit()
            return
        finally:
            self._frame_poll_in_flight = False
        if frame is None:
            self.frame_unavailable.emit()
        else:
            self.frame_updated.emit(frame)
