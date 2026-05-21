"""Unified findings protocol — shared envelope for all investigation findings."""

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FindingType = Literal[
    "metric_monitor",
    "dimension_contribution",
    "trend_analysis",
    "segment_stability",
    "strategy_impact",
]


class BaseFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    finding_type: FindingType
    metric_name: str
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
