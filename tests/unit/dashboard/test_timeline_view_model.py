from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.timeline_view_model import (
    TIMELINE_PAGE_SIZE,
    TimelineViewModel,
)
from PySide6.QtWidgets import QApplication


@pytest.mark.asyncio
async def test_emits_items_from_list_events(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.list_events.return_value = {"items": [{"id": "1"}, {"id": "2"}], "next_cursor": None}

    vm = TimelineViewModel(api_client)
    received: list[list] = []
    vm.events_updated.connect(received.append)

    await vm.refresh_async()

    assert received == [[{"id": "1"}, {"id": "2"}]]
    api_client.list_events.assert_awaited_once_with(limit=TIMELINE_PAGE_SIZE)
