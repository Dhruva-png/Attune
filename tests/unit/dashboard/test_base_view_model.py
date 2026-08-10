from __future__ import annotations

import asyncio

import httpx
import pytest
from attune.dashboard.viewmodels.base import PollingViewModel
from PySide6.QtWidgets import QApplication


class _RecordingViewModel(PollingViewModel):
    def __init__(self, side_effect, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(interval_ms=60_000, parent=parent)
        self._side_effect = side_effect
        self.calls = 0

    async def refresh_async(self) -> None:
        self.calls += 1
        await self._side_effect()


@pytest.mark.asyncio
async def test_refresh_awaits_refresh_async(qt_app: QApplication) -> None:
    async def ok() -> None:
        return None

    vm = _RecordingViewModel(ok)
    vm.refresh()
    await asyncio.sleep(0)

    assert vm.calls == 1


@pytest.mark.asyncio
async def test_http_error_is_caught_and_surfaced_as_error_signal(qt_app: QApplication) -> None:
    async def boom() -> None:
        raise httpx.ConnectError("connection refused")

    vm = _RecordingViewModel(boom)
    errors: list[str] = []
    vm.error_occurred.connect(errors.append)

    vm.refresh()
    await asyncio.sleep(0)

    assert len(errors) == 1
    assert "connection refused" in errors[0]


@pytest.mark.asyncio
async def test_start_triggers_immediate_refresh_and_arms_timer(qt_app: QApplication) -> None:
    async def ok() -> None:
        return None

    vm = _RecordingViewModel(ok)
    vm.start()
    await asyncio.sleep(0)

    assert vm.calls == 1
    assert vm._timer.isActive()

    vm.stop()
    assert not vm._timer.isActive()


@pytest.mark.asyncio
async def test_base_refresh_async_is_not_implemented(qt_app: QApplication) -> None:
    vm = PollingViewModel(interval_ms=60_000)

    with pytest.raises(NotImplementedError):
        await vm.refresh_async()
