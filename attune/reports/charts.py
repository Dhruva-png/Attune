from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from attune.core.entities.analytics_snapshot import AnalyticsSnapshot
from attune.core.events.schema import Event, EventType

# Print-friendly (white background) rather than the dashboard's dark theme —
# these figures get rasterized into PDF pages and standalone PNG exports,
# both of which are typically viewed/printed on a light background. This is
# the one place Plotly is used; the dashboard itself renders with custom
# QPainter widgets (see attune/dashboard/widgets/trend_chart.py) — sharing
# happens at the data layer (AnalyticsSnapshot/Event), not the renderer.
CHART_TEMPLATE = "plotly_white"
CHART_WIDTH = 900
CHART_HEIGHT = 380
BRAND_COLOR = "#6366f1"


def focus_score_over_time_figure(events: list[Event]) -> go.Figure | None:
    """Line chart of FOCUS_SCORE_UPDATED events across a session or day."""
    points = sorted(
        (
            (event.timestamp, event.metadata["score"])
            for event in events
            if event.type == EventType.FOCUS_SCORE_UPDATED and "score" in event.metadata
        ),
        key=lambda point: point[0],
    )
    if not points:
        return None

    timestamps, scores = zip(*points, strict=True)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=list(timestamps),
                y=list(scores),
                mode="lines",
                line={"color": BRAND_COLOR, "width": 2},
            )
        ]
    )
    fig.update_layout(
        template=CHART_TEMPLATE,
        title="Focus Score Over Time",
        xaxis_title="Time",
        yaxis_title="Focus Score",
        yaxis_range=[0, 100],
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        margin={"l": 60, "r": 30, "t": 50, "b": 50},
    )
    return fig


def daily_average_focus_figure(
    daily_snapshots: list[tuple[date, AnalyticsSnapshot]],
) -> go.Figure | None:
    """Bar chart of average focus score per day, for weekly/monthly reports."""
    points = [
        (day, snapshot.avg_focus_score)
        for day, snapshot in daily_snapshots
        if snapshot.avg_focus_score is not None
    ]
    if not points:
        return None

    days, scores = zip(*points, strict=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=[day.strftime("%a %m/%d") for day in days],
                y=list(scores),
                marker_color=BRAND_COLOR,
            )
        ]
    )
    fig.update_layout(
        template=CHART_TEMPLATE,
        title="Average Focus Score by Day",
        yaxis_title="Focus Score",
        yaxis_range=[0, 100],
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        margin={"l": 60, "r": 30, "t": 50, "b": 50},
    )
    return fig


def render_png(figure: go.Figure, *, scale: float = 2.0) -> bytes:
    result = figure.to_image(format="png", scale=scale)
    return bytes(result)
