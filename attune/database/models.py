from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
    """Mirrors docs/architecture/04-database-schema.md `sessions`."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'aborted')", name="ck_sessions_status"),
        CheckConstraint(
            "fatigue_level_end IN ('fresh', 'normal', 'tired', 'very_tired') "
            "OR fatigue_level_end IS NULL",
            name="ck_sessions_fatigue_level_end",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False, default="active")
    focus_score_avg: Mapped[float | None] = mapped_column(nullable=True)
    posture_score_avg: Mapped[float | None] = mapped_column(nullable=True)
    fatigue_level_end: Mapped[str | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class EventModel(Base):
    """Mirrors docs/architecture/04-database-schema.md `events` — the
    append-only source of truth every analytics rollup is derived from.
    """

    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_session_id", "session_id"),
        Index("idx_events_type", "type"),
        Index("idx_events_timestamp", "timestamp"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_events_confidence"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    source_module: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class AnalyticsSnapshotModel(Base):
    """Mirrors `analytics_snapshots` — cached rollups, always rebuildable
    from `events` (see docs/architecture/04-database-schema.md design notes).
    """

    __tablename__ = "analytics_snapshots"
    __table_args__ = (
        UniqueConstraint("period_type", "period_start", "session_id", name="idx_analytics_period"),
        CheckConstraint(
            "period_type IN ('daily', 'weekly', 'monthly')", name="ck_analytics_period_type"
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True
    )
    period_type: Mapped[str] = mapped_column(nullable=False)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    avg_focus_score: Mapped[float | None] = mapped_column(nullable=True)
    avg_posture_score: Mapped[float | None] = mapped_column(nullable=True)
    distraction_count: Mapped[int] = mapped_column(nullable=False, default=0)
    break_count: Mapped[int] = mapped_column(nullable=False, default=0)
    longest_break_seconds: Mapped[int | None] = mapped_column(nullable=True)
    best_hours: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    worst_hours: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    raw_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class ReportModel(Base):
    """Mirrors `reports` — generated export/PDF artifacts."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('daily', 'weekly', 'monthly', 'session')", name="ck_reports_type"
        ),
        CheckConstraint("format IN ('pdf', 'csv', 'json', 'png')", name="ck_reports_format"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(nullable=False)
    format: Mapped[str] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class SettingsModel(Base):
    """Mirrors `settings` — a single-row table (one local user, no accounts)."""

    __tablename__ = "settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    camera: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    llm: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    privacy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notifications: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    performance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    theme: Mapped[str] = mapped_column(nullable=False, default="dark")
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
