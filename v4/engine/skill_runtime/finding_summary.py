"""Finding summary skill — synthesize investigation conclusion."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models.conclusion import InvestigationConclusion, LlmSynthesisResult
from models.contribution import ContributionFinding
from models.metric_monitor import AttributionHint, MetricMonitorFinding
from prompts.finding_summary import SYSTEM_PROMPT, build_user_prompt
from services.llm import complete_synthesis

logger = logging.getLogger(__name__)

_RISK_DIRECTION_MAP = {
    AttributionHint.RISK_DETERIORATION: "deterioration",
    AttributionHint.RISK_IMPROVEMENT: "improvement",
    AttributionHint.NEUTRAL: "stable",
}


class FindingSummarySkill:
    def run(
        self,
        metric_monitor: MetricMonitorFinding,
        contributors: list[ContributionFinding],
    ) -> InvestigationConclusion:
        if not contributors:
            raise ValueError("contributors must not be empty")

        sorted_contributors = sorted(contributors, key=lambda c: c.rank)
        synthesis = self._synthesize(
            self._build_findings_payload(metric_monitor, sorted_contributors),
            metric_monitor,
            sorted_contributors,
        )

        return InvestigationConclusion(
            conclusion_id=str(uuid4()),
            metric_name=metric_monitor.metric_name,
            risk_direction=_RISK_DIRECTION_MAP.get(
                metric_monitor.attribution_hint, "stable"
            ),
            primary_driver=_driver_label(sorted_contributors[0]),
            secondary_drivers=[_driver_label(c) for c in sorted_contributors[1:]],
            business_summary=synthesis.business_summary,
            risk_hypothesis=synthesis.risk_hypothesis,
            recommended_actions=synthesis.recommended_actions,
            confidence=self._compute_confidence(
                metric_monitor.delta_pp, sorted_contributors[0]
            ),
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _compute_confidence(portfolio_delta_pp: float, top: ContributionFinding) -> float:
        denom = abs(portfolio_delta_pp)
        if denom < 1e-9:
            return 0.0
        return round(min(1.0, abs(top.contribution_pp) / denom), 4)

    @staticmethod
    def _build_findings_payload(
        metric_monitor: MetricMonitorFinding,
        contributors: list[ContributionFinding],
    ) -> dict[str, Any]:
        return {
            "metric_monitor": metric_monitor.model_dump(mode="json"),
            "top_contributors": [c.model_dump(mode="json") for c in contributors],
        }

    def _synthesize(
        self,
        findings_payload: dict[str, Any],
        metric_monitor: MetricMonitorFinding,
        contributors: list[ContributionFinding],
    ) -> LlmSynthesisResult:
        llm_result = complete_synthesis(SYSTEM_PROMPT, build_user_prompt(findings_payload))
        if llm_result is not None:
            return llm_result
        return _fallback_synthesis(metric_monitor, contributors)


def _driver_label(contributor: ContributionFinding) -> str:
    return f"{contributor.dimension_name}={contributor.dimension_value}"


def _fallback_synthesis(
    metric_monitor: MetricMonitorFinding,
    contributors: list[ContributionFinding],
) -> LlmSynthesisResult:
    top = contributors[0]
    label = f"{top.dimension_name}={top.dimension_value}"
    return LlmSynthesisResult(
        business_summary=(
            f"{metric_monitor.metric_name.upper()} moved {metric_monitor.delta_pp:+.2f}pp; "
            f"main driver {label} ({top.contribution_pp:+.2f}pp)."
        ),
        risk_hypothesis=f"Pattern concentrated in {label}.",
        recommended_actions=[f"Review {label} segment policy."],
    )
