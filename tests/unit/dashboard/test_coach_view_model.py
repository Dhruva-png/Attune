from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.coach_view_model import CoachViewModel
from PySide6.QtWidgets import QApplication


@pytest.mark.asyncio
async def test_emits_insights_from_weekly_period(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_coach_insights.return_value = {
        "insights": [{"text": "You focus best before noon.", "confidence": 0.8}]
    }

    vm = CoachViewModel(api_client)
    received: list[list] = []
    vm.insights_updated.connect(received.append)

    await vm.refresh_async()

    api_client.get_coach_insights.assert_awaited_once_with(period="weekly")
    assert received == [[{"text": "You focus best before noon.", "confidence": 0.8}]]
