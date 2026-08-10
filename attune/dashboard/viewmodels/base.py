from __future__ import annotations

import asyncio

import httpx
from PySide6.QtCore import QObject, QTimer, Signal


class PollingViewModel(QObject):
    """Base for viewmodels that periodically refresh from the API.

    Subclasses implement refresh_async() and emit their own success
    signal(s); network/HTTP failures are caught here once and surfaced via
    error_occurred rather than crashing the UI thread.
    """

    error_occurred = Signal(str)

    def __init__(self, interval_ms: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._interval_ms = interval_ms

    def start(self) -> None:
        self.refresh()
        self._timer.start(self._interval_ms)

    def stop(self) -> None:
        self._timer.stop()

    def refresh(self) -> None:
        asyncio.ensure_future(self._safe_refresh())

    async def _safe_refresh(self) -> None:
        try:
            await self.refresh_async()
        except httpx.HTTPError as exc:
            self.error_occurred.emit(str(exc))

    async def refresh_async(self) -> None:
        raise NotImplementedError
