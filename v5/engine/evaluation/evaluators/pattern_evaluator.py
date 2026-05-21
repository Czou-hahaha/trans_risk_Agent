"""Deterministic pattern confidence and stability evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from evaluation.evaluators._scoring import score_from_issues
from evaluation.schemas.evaluation_result import EvaluationResult
from intelligence_memory.patterns.schemas.detected_pattern import DetectedPattern

MIN_PATTERN_CONFIDENCE = 0.35
MIN_OCCURRENCE_RATIO = 0.6


class PatternEvaluator:
    """Evaluate recurring pattern recurrence stability and confidence."""

    def evaluate(
        self,
        patterns: list[DetectedPattern],
        *,
        investigation_id: str | None = None,
        min_occurrences: int = 3,
    ) -> EvaluationResult:
        issues: list[str] = []
        recommendations: list[str] = []
        generated_at = datetime.now(timezone.utc)

        scoped = patterns
        if investigation_id:
            scoped = [
                p
                for p in patterns
                if investigation_id in p.investigation_ids
            ]

        if not scoped:
            return EvaluationResult(
                evaluation_type="pattern_confidence",
                evaluation_score=1.0,
                detected_issues=[],
                recommendations=[
                    "No recurring patterns linked to this investigation; portfolio patterns may still exist."
                ],
                generated_at=generated_at,
            )

        confidences = [p.confidence_score for p in scoped]
        avg_confidence = sum(confidences) / len(confidences)

        for pattern in scoped:
            if pattern.confidence_score < MIN_PATTERN_CONFIDENCE:
                issues.append(
                    f"low_pattern_confidence:{pattern.pattern_type}:{pattern.pattern_id}"
                )
            ratio = pattern.occurrence_count / max(min_occurrences, 1)
            if ratio < MIN_OCCURRENCE_RATIO:
                issues.append(
                    f"unstable_recurrence:{pattern.pattern_type}:"
                    f"{pattern.occurrence_count}/{min_occurrences}"
                )
            inv_count = len(pattern.investigation_ids)
            if inv_count < min_occurrences:
                issues.append(
                    f"weak_cross_investigation_consistency:{pattern.pattern_type}:"
                    f"{inv_count}_investigations"
                )
            if not pattern.supporting_findings:
                issues.append(f"missing_supporting_findings:{pattern.pattern_id}")

        if any(i.startswith("low_pattern_confidence") for i in issues):
            recommendations.append(
                "Increase observation window or min_occurrences before promoting pattern alerts."
            )
        if any(i.startswith("unstable_recurrence") for i in issues):
            recommendations.append(
                "Verify segment/strategy signals are stable across consecutive investigations."
            )

        base_score = round(min(1.0, avg_confidence), 4)
        penalty_score = score_from_issues(len(issues), weight=0.08)
        final_score = round(min(base_score, penalty_score), 4)

        return EvaluationResult(
            evaluation_type="pattern_confidence",
            evaluation_score=final_score,
            detected_issues=issues,
            recommendations=_dedupe(recommendations),
            generated_at=generated_at,
        )


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
