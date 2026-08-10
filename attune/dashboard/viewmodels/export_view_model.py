from __future__ import annotations

import asyncio

import httpx
from PySide6.QtCore import QObject, Signal

from attune.dashboard.api_client import ApiClient

POLL_INTERVAL_SECONDS = 0.5
POLL_TIMEOUT_SECONDS = 30.0


class ExportError(Exception):
    pass


def _filename_from_response(response: httpx.Response, default: str) -> str:
    disposition: str = response.headers.get("content-disposition", "")
    if "filename=" in disposition:
        return str(disposition.split("filename=")[-1].strip('"'))
    return default


class ExportViewModel(QObject):
    """On-demand report export. json/csv resolve immediately; pdf/png go
    through the API's async job + polling flow (see
    docs/architecture/06-api-specification.md POST /export)."""

    export_started = Signal()
    export_ready = Signal(bytes, str)
    export_failed = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client

    def export(self, *, scope: str, target_id: str, export_format: str) -> None:
        asyncio.ensure_future(self._export_async(scope, target_id, export_format))

    async def _export_async(self, scope: str, target_id: str, export_format: str) -> None:
        self.export_started.emit()
        try:
            response = await self._api_client.export(
                scope=scope, target_id=target_id, export_format=export_format
            )
            if response.status_code == httpx.codes.ACCEPTED:
                report_id = response.json()["report_id"]
                content, filename = await self._poll_and_download(report_id)
            else:
                content = response.content
                filename = _filename_from_response(response, f"{scope}.{export_format}")
            self.export_ready.emit(content, filename)
        except (httpx.HTTPError, ExportError) as exc:
            self.export_failed.emit(str(exc))

    async def _poll_and_download(self, report_id: str) -> tuple[bytes, str]:
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT_SECONDS:
            status_body = await self._api_client.get_report_status(report_id)
            if status_body["status"] == "ready":
                response = await self._api_client.download_report(report_id)
                filename = _filename_from_response(response, f"{report_id}.pdf")
                return response.content, filename
            if status_body["status"] == "failed":
                raise ExportError(status_body.get("error") or "report generation failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
        raise ExportError("report generation timed out")
