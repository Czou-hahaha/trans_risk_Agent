"""API schemas for investigation evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationResultOut(BaseModel):
    evaluation_type: str
    evaluation_score: float
    detected_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime


class EvaluationMetricsOut(BaseModel):
    workflow_quality: float
    report_quality: float
    finding_confidence: float
    pattern_confidence: float
    overall_score: float


class InvestigationEvaluationOut(BaseModel):
    investigation_id: UUID
    metrics: EvaluationMetricsOut
    results: list[EvaluationResultOut]
    generated_at: datetime
