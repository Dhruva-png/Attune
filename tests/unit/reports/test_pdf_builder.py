from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from attune.analytics.timeline import TimelineEntry
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot, PeriodType
from attune.core.events.schema import Event, EventType
from attune.reports.charts import focus_score_over_time_figure, render_png
from attune.reports.pdf_builder import build_pdf_report


def _snapshot() -> AnalyticsSnapshot:
    return AnalyticsSnapshot(
        period_type=PeriodType.DAILY,
        period_start=date(2026, 1, 5),
        period_end=date(2026, 1, 5),
        avg_focus_score=76.5,
        avg_posture_score=80.1,
        distraction_count=11,
        break_count=4,
        longest_break_seconds=620,
        best_hours=["09:30-11:15"],
        worst_hours=["14:00-14:45"],
    )


def _timeline() -> list[TimelineEntry]:
    return [
        TimelineEntry(
            time="09:00", label="Started", event_type=EventType.SESSION_STARTED, confidence=1.0
        )
    ]


def test_build_pdf_report_produces_a_valid_pdf() -> None:
    pdf_bytes = build_pdf_report(
        title="Daily Report",
        period_label="2026-01-05",
        snapshot=_snapshot(),
        timeline=_timeline(),
        chart_png=None,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")


def test_build_pdf_report_embeds_chart_image() -> None:
    event = Event(
        session_id=uuid4(),
        type=EventType.FOCUS_SCORE_UPDATED,
        timestamp=datetime(2026, 1, 5, 9, 0),
        confidence=0.9,
        metadata={"score": 70.0},
        source_module="test",
    )
    fig = focus_score_over_time_figure([event])
    assert fig is not None
    chart_png = render_png(fig)

    pdf_bytes = build_pdf_report(
        title="Daily Report",
        period_label="2026-01-05",
        snapshot=_snapshot(),
        timeline=[],
        chart_png=chart_png,
    )
    pdf_bytes_without_chart = build_pdf_report(
        title="Daily Report",
        period_label="2026-01-05",
        snapshot=_snapshot(),
        timeline=[],
        chart_png=None,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > len(pdf_bytes_without_chart)


def test_build_pdf_report_handles_empty_timeline_and_no_hours() -> None:
    empty_snapshot = AnalyticsSnapshot(
        period_type=PeriodType.DAILY, period_start=date(2026, 1, 5), period_end=date(2026, 1, 5)
    )

    pdf_bytes = build_pdf_report(
        title="Daily Report",
        period_label="2026-01-05",
        snapshot=empty_snapshot,
        timeline=[],
        chart_png=None,
    )

    assert pdf_bytes.startswith(b"%PDF-")
