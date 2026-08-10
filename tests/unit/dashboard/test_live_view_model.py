from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.live_view_model import LiveViewModel
from PySide6.QtWidgets import QApplication


@pytest.mark.asyncio
async def test_emits_stats_updated_when_stats_present(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_live_stats.return_value = {"focus_score": 72.0}

    vm = LiveViewModel(api_client)
    received: list[dict] = []
    vm.stats_updated.connect(received.append)

    await vm.refresh_async()

    assert received == [{"focus_score": 72.0}]


@pytest.mark.asyncio
async def test_emits_stats_unavailable_when_no_active_session(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_live_stats.return_value = None

    vm = LiveViewModel(api_client)
    unavailable_count = 0

    def on_unavailable() -> None:
        nonlocal unavailable_count
        unavailable_count += 1

    vm.stats_unavailable.connect(on_unavailable)

    await vm.refresh_async()

    assert unavailable_count == 1
