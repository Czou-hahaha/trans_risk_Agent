"""API schemas for Executive Intelligence Dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IntelligenceItem(BaseModel):
    """Shared row for ranked intelligence cards."""

    id: str
    title: str
    summary: str
    metric_name: str | None = None
    dimension_name: str | None = None
    dimension_value: str | None = None
    occurrence_count: int = 0
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    investigation_ids: list[str] = Field(default_factory=list)
    pattern_type: str | None = None


class WeeklyHighlight(BaseModel):
    """Single bullet in the weekly risk intelligence summary."""

    category: str
    headline: str
    detail: str
    severity: str = "medium"


class WeeklyRiskSummary(BaseModel):
    """Auto-generated summary of the most important risk changes in the last 7 days."""

    period_label: str = "过去 7 天"
    generated_at: datetime
    headline: str
    highlights: list[WeeklyHighlight] = Field(default_factory=list)
    investigation_count: int = 0
    pattern_count: int = 0


class TrendIntelligence(BaseModel):
    """Risk / approval / volume-risk trend shifts across investigations."""

    risk_trend_shifts: list[IntelligenceItem] = Field(default_factory=list)
    approval_trend_shifts: list[IntelligenceItem] = Field(default_factory=list)
    volume_risk_tradeoffs: list[IntelligenceItem] = Field(default_factory=list)


class PatternIntelligence(BaseModel):
    """Cross-investigation recurring pattern signals."""

    recurring_patterns: list[IntelligenceItem] = Field(default_factory=list)
    historical_recurrence: list[IntelligenceItem] = Field(default_factory=list)
    cross_investigation_signals: list[IntelligenceItem] = Field(default_factory=list)


class ExecutiveIntelligenceOut(BaseModel):
    """Aggregate payload for the executive intelligence layer."""

    generated_at: datetime
    window_days: int = 7
    data_available: bool = True
    message: str | None = None

    top_recurring_contributors: list[IntelligenceItem] = Field(default_factory=list)
    most_unstable_segments: list[IntelligenceItem] = Field(default_factory=list)
    highest_risk_strategies: list[IntelligenceItem] = Field(default_factory=list)
    recurring_deterioration_patterns: list[IntelligenceItem] = Field(default_factory=list)
    weekly_summary: WeeklyRiskSummary

    trend_intelligence: TrendIntelligence = Field(default_factory=TrendIntelligence)
    pattern_intelligence: PatternIntelligence = Field(default_factory=PatternIntelligence)
