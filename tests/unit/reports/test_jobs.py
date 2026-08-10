from __future__ import annotations

from uuid import uuid4

from attune.reports.jobs import ReportJobStatus, ReportJobStore


def test_newly_created_job_is_processing() -> None:
    store = ReportJobStore()
    report_id = store.create()

    job = store.get(report_id)

    assert job is not None
    assert job.status == ReportJobStatus.PROCESSING
    assert job.content is None


def test_mark_ready_stores_content() -> None:
    store = ReportJobStore()
    report_id = store.create()

    store.mark_ready(
        report_id, content=b"pdf-bytes", media_type="application/pdf", filename="r.pdf"
    )

    job = store.get(report_id)
    assert job is not None
    assert job.status == ReportJobStatus.READY
    assert job.content == b"pdf-bytes"
    assert job.media_type == "application/pdf"
    assert job.filename == "r.pdf"


def test_mark_failed_stores_error() -> None:
    store = ReportJobStore()
    report_id = store.create()

    store.mark_failed(report_id, "boom")

    job = store.get(report_id)
    assert job is not None
    assert job.status == ReportJobStatus.FAILED
    assert job.error == "boom"


def test_get_returns_none_for_unknown_id() -> None:
    store = ReportJobStore()
    assert store.get(uuid4()) is None
