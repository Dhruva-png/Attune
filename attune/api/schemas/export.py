from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class ExportScope(StrEnum):
    SESSION = "session"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    PNG = "png"


class ExportRequest(BaseModel):
    scope: ExportScope
    target_id: str  # session UUID for scope=session, ISO date otherwise
    format: ExportFormat


class ExportJobResponse(BaseModel):
    """Returned with 202 when format is pdf/png — generation happens in the
    background; poll GET /reports/{report_id} for status."""

    report_id: UUID
    status: str


class ReportStatusResponse(BaseModel):
    status: str
    download_url: str | None = None
    error: str | None = None
