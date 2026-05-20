"""Investigation conclusion schema — output of finding_summary_skill."""

from datetime import datetime

from pydantic import BaseModel, Field


class LlmSynthesisResult(BaseModel):
    """Structured fields produced by LLM (or deterministic fallback)."""

    business_summary: str = Field(min_length=1)
    risk_hypothesis: str = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1)


class InvestigationConclusion(BaseModel):
    """Portfolio investigation conclusion synthesized from upstream findings."""

    conclusion_id: str
    metric_name: str
    risk_direction: str
    primary_driver: str
    secondary_drivers: list[str]
    business_summary: str
    risk_hypothesis: str
    recommended_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    generated_at: datetime
