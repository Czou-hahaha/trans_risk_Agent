"""Output schema for cross-investigation recurring risk patterns."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DetectedPattern(BaseModel):
    """A deterministic risk pattern discovered across historical investigations."""

    pattern_id: str
    pattern_type: str = Field(
        description=(
            "recurring_contributor | recurring_segment_instability | "
            "strategy_side_effect | approval_risk_shift | volume_risk_tradeoff"
        )
    )
    pattern_summary: str
    supporting_findings: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    first_detected_at: datetime
    last_detected_at: datetime
    investigation_ids: list[str] = Field(default_factory=list)
    dimension_name: str | None = None
    dimension_value: str | None = None
    metric_name: str | None = None
    occurrence_count: int = 0
