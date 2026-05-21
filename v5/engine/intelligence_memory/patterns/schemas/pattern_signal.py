"""Internal signals emitted by pattern detectors before aggregation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PatternSignal(BaseModel):
    """Atomic evidence unit for a detected risk pattern."""

    signal_type: str = Field(description="Detector-specific signal label")
    investigation_id: str
    finding_ids: list[str] = Field(default_factory=list)
    dimension_name: str | None = None
    dimension_value: str | None = None
    metric_name: str | None = None
    severity_magnitude: float = Field(
        default=0.0,
        description="Normalized magnitude (pp or pct) for confidence severity term",
    )
    generated_at: datetime
    metadata: dict[str, float | str | int] = Field(default_factory=dict)
