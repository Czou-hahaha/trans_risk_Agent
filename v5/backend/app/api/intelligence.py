"""Risk intelligence API — executive layer."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.schemas.executive import ExecutiveIntelligenceOut
from app.services.executive_intelligence_service import build_executive_intelligence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/executive", response_model=ExecutiveIntelligenceOut)
def executive_intelligence(
    weekly_days: int = Query(default=7, ge=1, le=90, description="Weekly summary window"),
    pattern_days: int = Query(default=30, ge=7, le=180, description="Pattern detection window"),
) -> ExecutiveIntelligenceOut:
    """Aggregate cross-investigation intelligence for the executive dashboard."""
    return build_executive_intelligence(
        weekly_window_days=weekly_days,
        pattern_window_days=pattern_days,
    )
