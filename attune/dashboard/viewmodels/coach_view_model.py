from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.base import PollingViewModel

COACH_POLL_INTERVAL_MS = 60_000


class CoachViewModel(PollingViewModel):
    insights_updated = Signal(list)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(interval_ms=COACH_POLL_INTERVAL_MS, parent=parent)
        self._api_client = api_client

    async def refresh_async(self) -> None:
        result = await self._api_client.get_coach_insights(period="weekly")
        self.insights_updated.emit(result["insights"])
