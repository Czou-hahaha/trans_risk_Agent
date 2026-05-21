"""Deterministic workflow routing and completeness evaluation."""

from __future__ import annotations

from datetime import date, datetime, timezone

from evaluation.evaluators._scoring import score_from_issues
from evaluation.schemas.evaluation_result import EvaluationResult
from workflow.result import InvestigationResult
from workflow.workflow_router import WorkflowRouter

ALWAYS_REQUIRED_SKILLS = frozenset({"metric_monitor", "finding_summary", "report_builder"})


class WorkflowEvaluator:
    """Evaluate workflow routing correctness and skill execution completeness."""

    def __init__(self, router: WorkflowRouter | None = None) -> None:
        self._router = router or WorkflowRouter()

    def evaluate(self, result: InvestigationResult) -> EvaluationResult:
        issues: list[str] = []
        recommendations: list[str] = []
        generated_at = datetime.now(timezone.utc)
        executed = set(result.executed_skills or [])

        if not executed:
            issues.append("no_executed_skills_recorded")
            return EvaluationResult(
                evaluation_type="workflow_consistency",
                evaluation_score=0.0,
                detected_issues=issues,
                recommendations=["Record executed_skills on InvestigationContext."],
                generated_at=generated_at,
            )

        missing_always = ALWAYS_REQUIRED_SKILLS - executed
        for skill in sorted(missing_always):
            issues.append(f"missing_required_skill:{skill}")

        expected = self._expected_skills(result)
        for skill in sorted(expected - executed):
            if skill in ALWAYS_REQUIRED_SKILLS:
                continue
            issues.append(f"planned_skill_not_executed:{skill}")

        for skill in sorted(executed - expected - {"report_builder"}):
            if skill in ALWAYS_REQUIRED_SKILLS:
                continue
            issues.append(f"unexpected_skill_executed:{skill}")

        if result.needs_investigation and "dimension_contribution" not in executed:
            issues.append("anomaly_without_contribution_skill")

        timeline_skills = {e.skill_name for e in result.timeline}
        for skill in ALWAYS_REQUIRED_SKILLS:
            if skill in executed and skill not in timeline_skills:
                issues.append(f"timeline_missing_event:{skill}")

        if issues:
            recommendations.extend(
                [
                    "Align WorkflowRouter plan with executed_skills after each skill stage.",
                    "Ensure skipped skills are marked skipped in timeline, not omitted.",
                ]
            )

        return EvaluationResult(
            evaluation_type="workflow_consistency",
            evaluation_score=score_from_issues(len(issues)),
            detected_issues=issues,
            recommendations=_unique(recommendations),
            generated_at=generated_at,
        )

    def _expected_skills(self, result: InvestigationResult) -> set[str]:
        monitor = result.monitor_finding
        if monitor is None:
            return set(ALWAYS_REQUIRED_SKILLS)

        plan = self._router.plan_initial(
            monitor,
            analysis_date=result.analysis_date,
        )
        if result.needs_investigation and result.trend_result is not None:
            plan = self._router.apply_trend(plan, result.trend_result.trend_finding)
        if result.contribution_findings:
            plan = self._router.apply_contribution(plan, result.contribution_findings)
        if result.segment_stability_result:
            plan = self._router.apply_segment_stability(
                plan, result.segment_stability_result.top_unstable_segments
            )

        if not result.needs_investigation:
            return {"metric_monitor", "report_builder"}

        expected = set(plan.executed_skills)
        expected.add("metric_monitor")
        expected.add("report_builder")
        if result.contribution_findings:
            expected.add("finding_summary")
        return expected


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
