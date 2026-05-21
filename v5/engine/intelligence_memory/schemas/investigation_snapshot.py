"""Investigation-level snapshot for cross-investigation queries."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class InvestigationSnapshot(BaseModel):
    """Lightweight investigation record stored alongside findings."""

    investigation_id: str
    metric_name: str
    analysis_date: date
    workflow_status: str
    findings_count: int = 0
    needs_investigation: bool | None = None
    trigger_reason: str | None = None
    generated_at: datetime = Field(
        description="Workflow completion timestamp (UTC)."
    )
