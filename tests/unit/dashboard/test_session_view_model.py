from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.session_view_model import SessionViewModel
from PySide6.QtWidgets import QApplication


async def _wait_until(predicate, timeout: float = 1.0) -> None:  # type: ignore[no-untyped-def]
    elapsed = 0.0
    step = 0.005
    while not predicate() and elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
    assert predicate(), "condition not met before timeout"


@pytest.mark.asyncio
async def test_start_session_sets_active_session_and_emits(qt_app: QApplication) -> None:
    session_id = str(uuid4())
    api_client = AsyncMock(spec=ApiClient)
    api_client.start_session.return_value = {"session_id": session_id, "status": "active"}

    vm = SessionViewModel(api_client)
    received: list[dict] = []
    vm.session_started.connect(received.append)

    vm.start_session(camera_index=2)
    await _wait_until(lambda: len(received) == 1)

    api_client.start_session.assert_awaited_once_with(2)
    assert vm.active_session == {"session_id": session_id, "status": "active"}
    assert received == [{"session_id": session_id, "status": "active"}]


@pytest.mark.asyncio
async def test_start_session_error_emits_error_and_leaves_no_active_session(
    qt_app: QApplication,
) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.start_session.side_effect = httpx.ConnectError("refused")

    vm = SessionViewModel(api_client)
    errors: list[str] = []
    vm.error_occurred.connect(errors.append)

    vm.start_session()
    await _wait_until(lambda: len(errors) == 1)

    assert vm.active_session is None


@pytest.mark.asyncio
async def test_end_session_converts_session_id_to_uuid_and_clears_active_session(
    qt_app: QApplication,
) -> None:
    session_id = str(uuid4())
    api_client = AsyncMock(spec=ApiClient)
    api_client.end_session.return_value = {"session_id": session_id, "status": "ended"}

    vm = SessionViewModel(api_client)
    vm.active_session = {"session_id": session_id, "status": "active"}
    received: list[dict] = []
    vm.session_ended.connect(received.append)

    vm.end_session()
    await _wait_until(lambda: len(received) == 1)

    api_client.end_session.assert_awaited_once_with(UUID(session_id))
    assert vm.active_session is None
    assert received == [{"session_id": session_id, "status": "ended"}]


@pytest.mark.asyncio
async def test_end_session_is_a_noop_when_no_active_session(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)

    vm = SessionViewModel(api_client)
    vm.end_session()
    await asyncio.sleep(0.01)

    api_client.end_session.assert_not_awaited()
