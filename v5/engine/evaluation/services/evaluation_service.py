"""Orchestrates deterministic investigation evaluation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from evaluation.evaluators import (
    FindingEvaluator,
    PatternEvaluator,
    ReportEvaluator,
    WorkflowEvaluator,
)
from evaluation.schemas.evaluation_metrics import EvaluationMetrics, InvestigationEvaluationBundle
from evaluation.schemas.evaluation_result import EvaluationResult
from intelligence_memory.patterns.pattern_detector import DetectorConfig
from intelligence_memory.patterns.recurring_pattern_engine import RecurringPatternEngine
from workflow.investigation_context import InvestigationContext
from workflow.result import InvestigationResult

logger = logging.getLogger(__name__)


class EvaluationService:
    """Run all evaluators and produce dashboard-ready quality metrics."""

    def __init__(
        self,
        *,
        pattern_engine: RecurringPatternEngine | None = None,
        session_factory: sessionmaker | None = None,
    ) -> None:
        self._finding_evaluator = FindingEvaluator()
        self._workflow_evaluator = WorkflowEvaluator()
        self._report_evaluator = ReportEvaluator()
        self._pattern_evaluator = PatternEvaluator()
        self._pattern_engine = pattern_engine
        if pattern_engine is not None:
            self._session_factory = session_factory
        else:
            self._pattern_engine = RecurringPatternEngine(
                session_factory=session_factory,
                auto_init=session_factory is None,
            )

    def evaluate_investigation(
        self,
        result: InvestigationResult,
        *,
        ctx: InvestigationContext | None = None,
        include_patterns: bool = True,
        pattern_config: DetectorConfig | None = None,
    ) -> InvestigationEvaluationBundle:
        """Evaluate finding, workflow, report, and optional pattern dimensions."""
        generated_at = datetime.now(timezone.utc)
        results: list[EvaluationResult] = []

        results.append(self._finding_evaluator.evaluate(list(result.findings)))
        results.append(self._workflow_evaluator.evaluate(result))
        results.append(self._report_evaluator.evaluate(result, ctx=ctx))

        pattern_score = 1.0
        if include_patterns:
            try:
                patterns = self._pattern_engine.detect_all(config=pattern_config)
                pattern_result = self._pattern_evaluator.evaluate(
                    patterns,
                    investigation_id=result.investigation_id,
                )
                results.append(pattern_result)
                pattern_score = pattern_result.evaluation_score
            except Exception:
                logger.warning(
                    "Pattern evaluation skipped for investigation_id=%s",
                    result.investigation_id,
                    exc_info=True,
                )
                results.append(
                    EvaluationResult(
                        evaluation_type="pattern_confidence",
                        evaluation_score=1.0,
                        detected_issues=["pattern_evaluation_unavailable"],
                        recommendations=["Initialize intelligence memory DB for pattern scoring."],
                        generated_at=generated_at,
                    )
                )

        metrics = self._build_metrics(results, pattern_score=pattern_score)
        return InvestigationEvaluationBundle(
            investigation_id=result.investigation_id,
            metrics=metrics,
            results=results,
            generated_at=generated_at,
        )

    def evaluate_from_payload(
        self,
        payload: dict,
        *,
        include_patterns: bool = True,
    ) -> InvestigationEvaluationBundle:
        """Evaluate from serialized InvestigationResult (e.g. report_json)."""
        result = InvestigationResult.model_validate(payload)
        return self.evaluate_investigation(result, include_patterns=include_patterns)

    @staticmethod
    def _build_metrics(
        results: list[EvaluationResult],
        *,
        pattern_score: float,
    ) -> EvaluationMetrics:
        by_type = {r.evaluation_type: r.evaluation_score for r in results}
        workflow = by_type.get("workflow_consistency", 1.0)
        report = by_type.get("report_completeness", 1.0)
        finding = by_type.get("finding_quality", 1.0)
        pattern = by_type.get("pattern_confidence", pattern_score)
        overall = round((workflow + report + finding + pattern) / 4.0, 4)
        return EvaluationMetrics(
            workflow_quality=workflow,
            report_quality=report,
            finding_confidence=finding,
            pattern_confidence=pattern,
            overall_score=overall,
        )
