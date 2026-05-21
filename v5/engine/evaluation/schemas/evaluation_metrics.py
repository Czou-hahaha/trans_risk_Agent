"""Aggregate quality metrics for dashboard display."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from evaluation.schemas.evaluation_result import EvaluationResult


class EvaluationMetrics(BaseModel):
    """Investigation Quality Panel — four quality dimensions."""

    workflow_quality: float = Field(ge=0.0, le=1.0)
    report_quality: float = Field(ge=0.0, le=1.0)
    finding_confidence: float = Field(ge=0.0, le=1.0)
    pattern_confidence: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)


class InvestigationEvaluationBundle(BaseModel):
    """Full evaluation package for one investigation."""

    investigation_id: str
    metrics: EvaluationMetrics
    results: list[EvaluationResult] = Field(default_factory=list)
    generated_at: datetime
