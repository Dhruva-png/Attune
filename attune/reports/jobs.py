from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4


class ReportJobStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass(slots=True)
class ReportJob:
    report_id: UUID
    status: ReportJobStatus = ReportJobStatus.PROCESSING
    content: bytes | None = None
    media_type: str | None = None
    filename: str | None = None
    error: str | None = None


class ReportJobStore:
    """In-memory job store for async PDF/PNG report generation.

    A local single-user desktop app has no need for a durable queue —
    jobs live only as long as the process, matching everything else this
    API generates on demand. See docs/architecture/06-api-specification.md's
    POST /export -> 202 + poll GET /reports/{id} -> download flow.
    """

    def __init__(self) -> None:
        self._jobs: dict[UUID, ReportJob] = {}

    def create(self) -> UUID:
        report_id = uuid4()
        self._jobs[report_id] = ReportJob(report_id=report_id)
        return report_id

    def mark_ready(
        self, report_id: UUID, *, content: bytes, media_type: str, filename: str
    ) -> None:
        self._jobs[report_id] = ReportJob(
            report_id=report_id,
            status=ReportJobStatus.READY,
            content=content,
            media_type=media_type,
            filename=filename,
        )

    def mark_failed(self, report_id: UUID, error: str) -> None:
        self._jobs[report_id] = ReportJob(
            report_id=report_id, status=ReportJobStatus.FAILED, error=error
        )

    def get(self, report_id: UUID) -> ReportJob | None:
        return self._jobs.get(report_id)
