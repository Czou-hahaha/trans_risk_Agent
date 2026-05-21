"""Segment 稳定性 finding 与结果模型。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from models.base_finding import BaseFinding


class SegmentStabilityFinding(BaseFinding):
    """单 segment 风险结构稳定性 finding。"""

    finding_type: Literal["segment_stability"] = "segment_stability"
    dimension_name: str
    dimension_value: str
    stability_score: float
    volatility_score: float
    volatility_level: str
    trend_direction: str
    consecutive_up_periods: int
    regime_shift_detected: bool
    segment_health: str
    current_metric_value: float
    baseline_metric_value: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class SegmentStabilityResult(BaseModel):
    metric_name: str
    dimension_name: str
    analysis_window_days: int
    top_unstable_segments: list[SegmentStabilityFinding]
    generated_at: datetime
