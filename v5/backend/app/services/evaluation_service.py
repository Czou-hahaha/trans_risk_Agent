"""Bridge backend API to engine evaluation layer."""

from __future__ import annotations

import logging
import sys
from uuid import UUID

from app.config import settings
from app.schemas.evaluation import (
    EvaluationMetricsOut,
    EvaluationResultOut,
    InvestigationEvaluationOut,
)

logger = logging.getLogger(__name__)

_ENGINE = settings.engine_root
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from evaluation import EvaluationService  # noqa: E402


def run_investigation_evaluation(
    investigation_id: UUID,
    report_payload: dict,
) -> InvestigationEvaluationOut:
    """Run deterministic evaluators on persisted investigation result."""
    svc = EvaluationService()
    bundle = svc.evaluate_from_payload(report_payload, include_patterns=True)
    return InvestigationEvaluationOut(
        investigation_id=investigation_id,
        metrics=EvaluationMetricsOut(
            workflow_quality=bundle.metrics.workflow_quality,
            report_quality=bundle.metrics.report_quality,
            finding_confidence=bundle.metrics.finding_confidence,
            pattern_confidence=bundle.metrics.pattern_confidence,
            overall_score=bundle.metrics.overall_score,
        ),
        results=[
            EvaluationResultOut(
                evaluation_type=r.evaluation_type,
                evaluation_score=r.evaluation_score,
                detected_issues=list(r.detected_issues),
                recommendations=list(r.recommendations),
                generated_at=r.generated_at,
            )
            for r in bundle.results
        ],
        generated_at=bundle.generated_at,
    )
