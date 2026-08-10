from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.analytics_view_model import AnalyticsViewModel
from PySide6.QtWidgets import QApplication


@pytest.mark.asyncio
async def test_fetches_daily_and_weekly_for_current_period(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_daily_report.return_value = {"avg_focus_score": 80.0}
    api_client.get_weekly_report.return_value = {"week_start": "2026-01-05"}

    vm = AnalyticsViewModel(api_client)
    daily_received: list[dict] = []
    weekly_received: list[dict] = []
    vm.daily_updated.connect(daily_received.append)
    vm.weekly_updated.connect(weekly_received.append)

    await vm.refresh_async()

    today = date.today()
    expected_week_start = today - timedelta(days=today.weekday())

    api_client.get_daily_report.assert_awaited_once_with(today)
    api_client.get_weekly_report.assert_awaited_once_with(expected_week_start)
    assert daily_received == [{"avg_focus_score": 80.0}]
    assert weekly_received == [{"week_start": "2026-01-05"}]
