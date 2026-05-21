"""Deterministic report completeness evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from evaluation.evaluators._scoring import score_from_issues
from evaluation.schemas.evaluation_result import EvaluationResult
from report.investigation_report_builder import InvestigationReportBuilder
from workflow.investigation_context import InvestigationContext
from workflow.result import InvestigationResult

MIN_EXECUTIVE_LEN = 40
PLACEHOLDER_MARKERS = (
    "not executed",
    "not available",
    "did not flag",
    "no dimension contribution",
)


class ReportEvaluator:
    """Evaluate report sections, summaries, and evidence coverage."""

    def evaluate(
        self,
        result: InvestigationResult,
        *,
        ctx: InvestigationContext | None = None,
    ) -> EvaluationResult:
        issues: list[str] = []
        recommendations: list[str] = []
        generated_at = datetime.now(timezone.utc)

        context = ctx or _context_from_result(result)
        sections = InvestigationReportBuilder().build_sections(context)

        if not (result.executive_summary or context.executive_summary):
            issues.append("missing_executive_summary")
        else:
            summary = result.executive_summary or context.executive_summary
            if len(summary.strip()) < MIN_EXECUTIVE_LEN:
                issues.append("weak_executive_summary")

        if result.needs_investigation and not result.findings:
            issues.append("empty_findings_for_anomaly_investigation")

        if result.trend_result and _is_placeholder(sections.trend_analysis.body):
            issues.append("missing_trend_section_content")

        if result.contribution_findings and _is_placeholder(sections.key_contributors.body):
            issues.append("missing_contributors_section_content")

        if result.segment_stability_result and result.segment_stability_result.top_unstable_segments:
            if _is_placeholder(sections.segment_stability.body):
                issues.append("missing_segment_section_content")

        if result.strategy_impact_result and result.strategy_impact_result.findings:
            if _is_placeholder(sections.strategy_impact.body):
                issues.append("missing_strategy_section_content")
            strat = result.strategy_impact_result.findings[0]
            if not strat.evidence:
                issues.append("strategy_section_missing_evidence_reference")

        if not sections.risk_recommendations.bullets:
            issues.append("empty_recommendations_section")

        if result.generated_report_path is None:
            issues.append("missing_generated_report_path")

        if issues:
            recommendations.extend(
                [
                    "Populate report sections when matching skill results exist.",
                    "Reference strategy evidence bullets (FPD7 / approval / volume deltas).",
                    "Ensure executive summary mentions top contributor and trend when present.",
                ]
            )

        return EvaluationResult(
            evaluation_type="report_completeness",
            evaluation_score=score_from_issues(len(issues)),
            detected_issues=issues,
            recommendations=_dedupe(recommendations),
            generated_at=generated_at,
        )


def _is_placeholder(body: str) -> bool:
    lower = body.lower()
    return any(marker in lower for marker in PLACEHOLDER_MARKERS)


def _context_from_result(result: InvestigationResult) -> InvestigationContext:
    ref = result.analysis_date
    cur = (ref, ref)
    return InvestigationContext(
        investigation_id=result.investigation_id,
        metric_name=result.metric_name,
        analysis_date=ref,
        current_period=cur,
        previous_period=cur,
        started_at=result.generated_at,
        findings=list(result.findings),
        executed_skills=list(result.executed_skills),
        executive_summary=result.executive_summary,
        monitor_finding=result.monitor_finding,
        trend_result=result.trend_result,
        contribution_findings=list(result.contribution_findings),
        segment_stability_result=result.segment_stability_result,
        strategy_impact_result=result.strategy_impact_result,
        investigation_conclusion=result.investigation_conclusion,
        generated_report_path=result.generated_report_path,
    )


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
