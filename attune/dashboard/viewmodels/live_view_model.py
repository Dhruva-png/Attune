from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.base import PollingViewModel

LIVE_STATS_POLL_INTERVAL_MS = 2000


class LiveViewModel(PollingViewModel):
    stats_updated = Signal(dict)
    stats_unavailable = Signal()

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(interval_ms=LIVE_STATS_POLL_INTERVAL_MS, parent=parent)
        self._api_client = api_client

    async def refresh_async(self) -> None:
        stats: dict[str, Any] | None = await self._api_client.get_live_stats()
        if stats is None:
            self.stats_unavailable.emit()
        else:
            self.stats_updated.emit(stats)
