from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from attune.dashboard.api_client import ApiClient
from attune.dashboard.viewmodels.export_view_model import ExportViewModel
from PySide6.QtWidgets import QApplication


async def _wait_until(predicate, timeout: float = 1.0) -> None:  # type: ignore[no-untyped-def]
    elapsed = 0.0
    step = 0.005
    while not predicate() and elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
    assert predicate(), "condition not met before timeout"


def _sync_response(content: bytes, filename: str) -> httpx.Response:
    return httpx.Response(
        200,
        content=content,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
        request=httpx.Request("POST", "http://test/api/v1/export"),
    )


@pytest.mark.asyncio
async def test_sync_export_emits_ready_immediately(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.export.return_value = _sync_response(b'{"a": 1}', "daily-2026-01-05.json")

    vm = ExportViewModel(api_client)
    started = []
    ready = []
    vm.export_started.connect(lambda: started.append(True))
    vm.export_ready.connect(lambda content, filename: ready.append((content, filename)))

    vm.export(scope="daily", target_id="2026-01-05", export_format="json")
    await _wait_until(lambda: len(ready) == 1)

    assert started == [True]
    assert ready == [(b'{"a": 1}', "daily-2026-01-05.json")]
    api_client.export.assert_awaited_once_with(
        scope="daily", target_id="2026-01-05", export_format="json"
    )


@pytest.mark.asyncio
async def test_async_export_polls_until_ready_then_downloads(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.export.return_value = httpx.Response(
        202,
        json={"report_id": "abc123", "status": "processing"},
        request=httpx.Request("POST", "http://test/api/v1/export"),
    )
    api_client.get_report_status.side_effect = [
        {"status": "processing"},
        {"status": "ready", "download_url": "/api/v1/reports/abc123/download"},
    ]
    api_client.download_report.return_value = _sync_response(b"%PDF-1.4", "weekly-2026-01-05.pdf")

    vm = ExportViewModel(api_client)
    ready = []
    vm.export_ready.connect(lambda content, filename: ready.append((content, filename)))

    vm.export(scope="weekly", target_id="2026-01-05", export_format="pdf")
    await _wait_until(lambda: len(ready) == 1, timeout=2.0)

    assert ready == [(b"%PDF-1.4", "weekly-2026-01-05.pdf")]
    api_client.download_report.assert_awaited_once_with("abc123")


@pytest.mark.asyncio
async def test_async_export_failure_emits_export_failed(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.export.return_value = httpx.Response(
        202,
        json={"report_id": "abc123", "status": "processing"},
        request=httpx.Request("POST", "http://test/api/v1/export"),
    )
    api_client.get_report_status.return_value = {"status": "failed", "error": "no chart data"}

    vm = ExportViewModel(api_client)
    errors = []
    vm.export_failed.connect(errors.append)

    vm.export(scope="daily", target_id="2026-01-05", export_format="pdf")
    await _wait_until(lambda: len(errors) == 1, timeout=2.0)

    assert errors == ["no chart data"]


@pytest.mark.asyncio
async def test_http_error_emits_export_failed(qt_app: QApplication) -> None:
    api_client = AsyncMock(spec=ApiClient)
    api_client.export.side_effect = httpx.ConnectError("refused")

    vm = ExportViewModel(api_client)
    errors = []
    vm.export_failed.connect(errors.append)

    vm.export(scope="daily", target_id="2026-01-05", export_format="json")
    await _wait_until(lambda: len(errors) == 1)

    assert "refused" in errors[0]
