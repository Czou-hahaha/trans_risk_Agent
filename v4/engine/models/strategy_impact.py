"""策略影响 finding 与结果模型。"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from models.base_finding import BaseFinding


class StrategyImpactFinding(BaseFinding):
    """单策略上线前后影响 finding。"""

    finding_type: Literal["strategy_impact"] = "strategy_impact"
    strategy_name: str
    deployment_date: date
    before_window_days: int
    after_window_days: int
    approval_rate_before: float
    approval_rate_after: float
    approval_delta_pp: float
    fpd7_before: float
    fpd7_after: float
    fpd7_delta_pp: float
    volume_before: float
    volume_after: float
    volume_delta_pct: float
    risk_reduction_efficiency: float
    strategy_effectiveness: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class StrategyImpactResult(BaseModel):
    strategy_name: str
    deployment_date: date
    findings: list[StrategyImpactFinding]
    generated_at: datetime
