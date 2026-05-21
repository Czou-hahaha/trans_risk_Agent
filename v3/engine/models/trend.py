"""趋势分析 finding 与结果模型。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from models.base_finding import BaseFinding


class TrendFinding(BaseFinding):
    """时序风险 finding（确定性趋势分析）。"""

    finding_type: Literal["trend_analysis"] = "trend_analysis"
    trend_direction: str
    trend_strength: str
    rolling_change_pp: float
    slope_value: float
    volatility_score: float
    volatility_level: str
    consecutive_up_periods: int
    anomaly_periods: list[str] = Field(default_factory=list)
    current_value: float
    baseline_value: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class TrendAnalysisResult(BaseModel):
    metric_name: str
    analysis_window_days: int
    aggregation_level: str
    trend_finding: TrendFinding
    generated_at: datetime
