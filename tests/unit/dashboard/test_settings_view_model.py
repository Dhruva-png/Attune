from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.settings_view_model import SettingsViewModel
from PySide6.QtWidgets import QApplication


async def _wait_until(predicate, timeout: float = 1.0) -> None:  # type: ignore[no-untyped-def]
    elapsed = 0.0
    step = 0.005
    while not predicate() and elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
    assert predicate(), "condition not met before timeout"


@pytest.mark.asyncio
async def test_load_emits_settings_loaded(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_settings.return_value = {"llm_provider": "ollama"}

    vm = SettingsViewModel(api_client)
    received: list[dict] = []
    vm.settings_loaded.connect(received.append)

    vm.load()
    await _wait_until(lambda: len(received) == 1)

    assert received == [{"llm_provider": "ollama"}]


@pytest.mark.asyncio
async def test_load_error_emits_error_occurred(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.get_settings.side_effect = httpx.ConnectError("refused")

    vm = SettingsViewModel(api_client)
    errors: list[str] = []
    vm.error_occurred.connect(errors.append)

    vm.load()
    await _wait_until(lambda: len(errors) == 1)

    assert "refused" in errors[0]


@pytest.mark.asyncio
async def test_save_emits_loaded_then_succeeded(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.update_settings.return_value = {"llm_provider": "openai"}

    vm = SettingsViewModel(api_client)
    loaded: list[dict] = []
    succeeded_count = 0

    def on_succeeded() -> None:
        nonlocal succeeded_count
        succeeded_count += 1

    vm.settings_loaded.connect(loaded.append)
    vm.save_succeeded.connect(on_succeeded)

    vm.save({"llm_provider": "openai"})
    await _wait_until(lambda: succeeded_count == 1)

    assert loaded == [{"llm_provider": "openai"}]
    api_client.update_settings.assert_awaited_once_with({"llm_provider": "openai"})


@pytest.mark.asyncio
async def test_save_error_emits_error_occurred_and_not_succeeded(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.update_settings.side_effect = httpx.ConnectError("refused")

    vm = SettingsViewModel(api_client)
    errors: list[str] = []
    succeeded_count = 0

    def on_succeeded() -> None:
        nonlocal succeeded_count
        succeeded_count += 1

    vm.error_occurred.connect(errors.append)
    vm.save_succeeded.connect(on_succeeded)

    vm.save({"llm_provider": "openai"})
    await _wait_until(lambda: len(errors) == 1)

    assert succeeded_count == 0
