"""Evaluation output schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Deterministic evaluation outcome for one dimension of investigation quality."""

    evaluation_type: str = Field(
        description=(
            "finding_quality | workflow_consistency | "
            "report_completeness | pattern_confidence"
        )
    )
    evaluation_score: float = Field(ge=0.0, le=1.0)
    detected_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime
