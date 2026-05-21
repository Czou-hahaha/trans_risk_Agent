"""SQLAlchemy models for risk intelligence persistence."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IntelligenceBase(DeclarativeBase):
    pass


class StoredFindingRow(IntelligenceBase):
    __tablename__ = "stored_findings"
    __table_args__ = (
        Index("ix_stored_findings_investigation_id", "investigation_id"),
        Index("ix_stored_findings_metric_name", "metric_name"),
        Index("ix_stored_findings_dimension", "dimension_name", "dimension_value"),
    )

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dimension_value: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contribution_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    approval_delta_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_delta_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestigationSnapshotRow(IntelligenceBase):
    __tablename__ = "investigation_snapshots"

    investigation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(32), nullable=False)
    findings_count: Mapped[int] = mapped_column(nullable=False, default=0)
    needs_investigation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
