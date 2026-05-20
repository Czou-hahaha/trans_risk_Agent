"""Contribution finding schemas — extends unified findings protocol."""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from models.base_finding import BaseFinding


class AttributionContext(str, Enum):
    """Derived from portfolio_delta_pp inside skill; used for ranking only."""

    RISK_DETERIORATION = "risk_deterioration"
    RISK_IMPROVEMENT = "risk_improvement"
    NEUTRAL = "neutral"


class ContributionFinding(BaseFinding):
    """Single dimension-value contributor — analysis numbers only, no business severity."""

    finding_type: Literal["dimension_contribution"] = "dimension_contribution"
    dimension_name: str
    dimension_value: str
    current_value: float = Field(
        description="Period metric in percentage points, e.g. 2.8 for 2.8%"
    )
    previous_value: float
    delta_pp: float
    contribution_pp: float
    rank: int


class DimensionContributionResult(BaseModel):
    """Aggregated output of a full contribution analysis run."""

    metric_name: str
    attribution_context: AttributionContext = Field(
        description="Auto-derived from portfolio_delta_pp for ranking"
    )
    current_period_start: date
    current_period_end: date
    previous_period_start: date
    previous_period_end: date
    portfolio_current_value: float | None = None
    portfolio_previous_value: float | None = None
    portfolio_delta_pp: float | None = None
    top_contributors: list[ContributionFinding]
    generated_at: datetime
