"""Pydantic schema for persisted investigation findings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StoredFinding(BaseModel):
    """Structured row written to `stored_findings`."""

    finding_id: str
    investigation_id: str
    metric_name: str
    finding_type: str
    dimension_name: str | None = None
    dimension_value: str | None = None
    summary: str
    severity: str | None = None
    contribution_pp: float | None = None
    delta_pp: float | None = None
    approval_delta_pp: float | None = None
    volume_delta_pct: float | None = None
    generated_at: datetime
