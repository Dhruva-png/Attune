from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.base import PollingViewModel

TIMELINE_POLL_INTERVAL_MS = 5000
TIMELINE_PAGE_SIZE = 50


class TimelineViewModel(PollingViewModel):
    events_updated = Signal(list)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(interval_ms=TIMELINE_POLL_INTERVAL_MS, parent=parent)
        self._api_client = api_client

    async def refresh_async(self) -> None:
        result = await self._api_client.list_events(limit=TIMELINE_PAGE_SIZE)
        self.events_updated.emit(result["items"])
