"""Deterministic finding quality evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from evaluation.evaluators._scoring import score_from_issues
from evaluation.schemas.evaluation_result import EvaluationResult

EVIDENCE_REQUIRED_TYPES = frozenset(
    {
        "metric_monitor",
        "dimension_contribution",
        "trend_analysis",
        "segment_stability",
        "strategy_impact",
    }
)

MIN_SUMMARY_LEN = 12
DELTA_CONFLICT_PP = 0.5


class FindingEvaluator:
    """Evaluate finding consistency, duplicates, and evidence completeness."""

    def evaluate(self, findings: list[dict[str, Any]]) -> EvaluationResult:
        issues: list[str] = []
        recommendations: list[str] = []
        generated_at = datetime.now(timezone.utc)

        if not findings:
            issues.append("no_findings_recorded")
            recommendations.append("Ensure workflow skills append findings to context.")
            return EvaluationResult(
                evaluation_type="finding_quality",
                evaluation_score=0.0,
                detected_issues=issues,
                recommendations=recommendations,
                generated_at=generated_at,
            )

        self._check_duplicates(findings, issues, recommendations)
        self._check_consistency(findings, issues, recommendations)
        self._check_evidence(findings, issues, recommendations)
        self._check_summaries(findings, issues, recommendations)

        return EvaluationResult(
            evaluation_type="finding_quality",
            evaluation_score=score_from_issues(len(issues)),
            detected_issues=issues,
            recommendations=recommendations,
            generated_at=generated_at,
        )

    def _check_duplicates(
        self,
        findings: list[dict[str, Any]],
        issues: list[str],
        recommendations: list[str],
    ) -> None:
        seen: dict[tuple[str, str, str], str] = {}
        for f in findings:
            ftype = str(f.get("finding_type", ""))
            dim_name = str(f.get("dimension_name") or "")
            dim_value = str(f.get("dimension_value") or f.get("strategy_name") or "")
            key = (ftype, dim_name, dim_value)
            fid = str(f.get("finding_id", ""))
            if key in seen and key[2]:
                issues.append(f"duplicate_finding:{ftype}:{dim_name}={dim_value}")
            elif key[2] or ftype == "metric_monitor":
                seen[key] = fid
        if any(i.startswith("duplicate_finding") for i in issues):
            recommendations.append(
                "Deduplicate findings before persistence; one row per dimension/strategy per investigation."
            )

    def _check_consistency(
        self,
        findings: list[dict[str, Any]],
        issues: list[str],
        recommendations: list[str],
    ) -> None:
        by_dim: dict[tuple[str, str, str], list[float]] = {}
        for f in findings:
            ftype = str(f.get("finding_type", ""))
            dim_name = f.get("dimension_name")
            dim_value = f.get("dimension_value")
            if not dim_name or not dim_value:
                continue
            delta = _delta_pp(f)
            if delta is None:
                continue
            by_dim.setdefault((ftype, str(dim_name), str(dim_value)), []).append(delta)

        for (ftype, dim_name, dim_value), deltas in by_dim.items():
            if len(deltas) < 2:
                continue
            if max(deltas) - min(deltas) > DELTA_CONFLICT_PP:
                issues.append(
                    f"inconsistent_delta:{ftype}:{dim_name}={dim_value}:"
                    f"{min(deltas):.2f}..{max(deltas):.2f}pp"
                )
        if any(i.startswith("inconsistent_delta") for i in issues):
            recommendations.append(
                "Align delta_pp / contribution_pp across findings for the same segment."
            )

    def _check_evidence(
        self,
        findings: list[dict[str, Any]],
        issues: list[str],
        recommendations: list[str],
    ) -> None:
        for f in findings:
            ftype = str(f.get("finding_type", ""))
            if ftype not in EVIDENCE_REQUIRED_TYPES:
                continue
            evidence = f.get("evidence")
            if not isinstance(evidence, dict) or len(evidence) == 0:
                issues.append(f"missing_evidence:{ftype}:{f.get('finding_id', 'unknown')}")
        if any(i.startswith("missing_evidence") for i in issues):
            recommendations.append(
                "Populate evidence dict on each skill finding (windows, metric_deltas, sample sizes)."
            )

    def _check_summaries(
        self,
        findings: list[dict[str, Any]],
        issues: list[str],
        recommendations: list[str],
    ) -> None:
        for f in findings:
            summary = str(f.get("summary") or "").strip()
            if len(summary) < MIN_SUMMARY_LEN:
                issues.append(
                    f"weak_summary:{f.get('finding_type')}:{f.get('finding_id', 'unknown')}"
                )
        if any(i.startswith("weak_summary") for i in issues):
            recommendations.append("Expand finding summaries with metric deltas and segment labels.")


def _delta_pp(finding: dict[str, Any]) -> float | None:
    for key in ("delta_pp", "contribution_pp", "rolling_change_pp", "fpd7_delta_pp"):
        val = finding.get(key)
        if val is not None:
            return float(val)
    return None
