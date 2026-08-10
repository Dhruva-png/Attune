from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from attune.analytics.timeline import TimelineEntry
from attune.core.entities.analytics_snapshot import AnalyticsSnapshot

BRAND_COLOR = colors.HexColor("#6366f1")
MUTED_COLOR = colors.HexColor("#6b7280")
BORDER_COLOR = colors.HexColor("#e5e7eb")

# Reflects docs/architecture/06-api-specification.md's daily/weekly report
# shape — every field the API returns gets a section here, so a generated
# PDF is a strict superset of what the JSON export already contains.
_METRIC_LABELS = (
    "Avg Focus Score",
    "Avg Posture Score",
    "Distractions",
    "Breaks",
    "Longest Break",
)


def _fmt_score(value: float | None) -> str:
    return f"{value:.0f}" if value is not None else "—"


def _fmt_seconds(value: int | None) -> str:
    if value is None:
        return "—"
    minutes, seconds = divmod(value, 60)
    return f"{minutes}m {seconds}s"


def _fmt_hours(hours: list[str]) -> str:
    return ", ".join(hours) if hours else "—"


def _metrics_table(snapshot: AnalyticsSnapshot) -> Table:
    values = (
        _fmt_score(snapshot.avg_focus_score),
        _fmt_score(snapshot.avg_posture_score),
        str(snapshot.distraction_count),
        str(snapshot.break_count),
        _fmt_seconds(snapshot.longest_break_seconds),
    )
    table = Table([list(_METRIC_LABELS), list(values)], colWidths=[1.4 * inch] * 5)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTSIZE", (0, 1), (-1, 1), 13),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]
        )
    )
    return table


def _timeline_table(timeline: list[TimelineEntry], styles) -> Table:  # type: ignore[no-untyped-def]
    header = ["Time", "Event", "Confidence"]
    rows = [
        [entry.time, entry.label, f"{entry.confidence:.0%}"]
        for entry in timeline[:100]  # a page-length cap; the raw JSON/CSV export has the rest
    ]
    table = Table([header, *rows], colWidths=[0.9 * inch, 4.0 * inch, 1.1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
            ]
        )
    )
    return table


def build_pdf_report(
    *,
    title: str,
    period_label: str,
    snapshot: AnalyticsSnapshot,
    timeline: list[TimelineEntry],
    chart_png: bytes | None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title=title,
    )

    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "Brand", parent=styles["Heading1"], textColor=BRAND_COLOR, fontSize=22, spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], textColor=MUTED_COLOR, fontSize=12, spaceAfter=18
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=13, spaceBefore=18, spaceAfter=8
    )

    story: list[object] = [
        Paragraph("Attune", brand_style),
        Paragraph(f"{title} — {period_label}", subtitle_style),
        _metrics_table(snapshot),
    ]

    if snapshot.best_hours or snapshot.worst_hours:
        story.append(Paragraph("Best &amp; Worst Hours", section_style))
        story.append(
            Paragraph(
                f"Best: {_fmt_hours(snapshot.best_hours)}"
                f"&nbsp;&nbsp;&nbsp;Worst: {_fmt_hours(snapshot.worst_hours)}",
                styles["Normal"],
            )
        )

    if chart_png is not None:
        story.append(Paragraph("Trend", section_style))
        story.append(Image(io.BytesIO(chart_png), width=6.3 * inch, height=6.3 * inch * 380 / 900))

    if timeline:
        story.append(Paragraph("Timeline", section_style))
        story.append(_timeline_table(timeline, styles))
    else:
        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                "No event timeline for this period — export as JSON/CSV for full event data.",
                styles["Normal"],
            )
        )

    doc.build(story)
    return buffer.getvalue()
