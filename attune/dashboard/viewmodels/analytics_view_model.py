from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.base import PollingViewModel

ANALYTICS_POLL_INTERVAL_MS = 30_000


class AnalyticsViewModel(PollingViewModel):
    daily_updated = Signal(dict)
    weekly_updated = Signal(dict)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(interval_ms=ANALYTICS_POLL_INTERVAL_MS, parent=parent)
        self._api_client = api_client

    async def refresh_async(self) -> None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        daily = await self._api_client.get_daily_report(today)
        weekly = await self._api_client.get_weekly_report(week_start)

        self.daily_updated.emit(daily)
        self.weekly_updated.emit(weekly)
