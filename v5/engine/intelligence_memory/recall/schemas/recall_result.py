"""Structured output for historical recall queries."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from intelligence_memory.recall.schemas.recurring_pattern import RecurringPattern
from intelligence_memory.schemas.investigation_snapshot import InvestigationSnapshot
from intelligence_memory.schemas.stored_finding import StoredFinding


class MatchedInvestigation(BaseModel):
    """Investigation matched by recall or similarity logic."""

    investigation_id: str
    metric_name: str
    analysis_date: date | None = None
    similarity_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)


class RecallResult(BaseModel):
    """Unified recall response for API and future frontend."""

    matched_investigations: list[MatchedInvestigation] = Field(default_factory=list)
    recurring_patterns: list[RecurringPattern] = Field(default_factory=list)
    historical_frequency: dict[str, int] = Field(default_factory=dict)
    similarity_score: float | None = Field(
        default=None,
        description="Aggregate score for similarity queries; max among matches.",
    )
    findings: list[StoredFinding] = Field(
        default_factory=list,
        description="Raw findings when lookup returns detail rows.",
    )
    recent_investigations: list[InvestigationSnapshot] = Field(default_factory=list)
