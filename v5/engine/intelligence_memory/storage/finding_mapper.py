"""Map runtime finding payloads to StoredFinding rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from intelligence_memory.schemas.stored_finding import StoredFinding


def finding_dict_to_stored(
    finding: dict[str, Any],
    *,
    investigation_id: str,
    metric_name: str | None = None,
) -> StoredFinding:
    """Normalize a skill finding dict into a persistence record."""
    finding_type = str(finding.get("finding_type", "unknown"))
    resolved_metric = metric_name or str(finding.get("metric_name", ""))

    dimension_name: str | None = None
    dimension_value: str | None = None
    severity: str | None = None
    contribution_pp: float | None = None
    delta_pp: float | None = None
    approval_delta_pp: float | None = None
    volume_delta_pct: float | None = None

    if finding_type == "dimension_contribution":
        dimension_name = _str_or_none(finding.get("dimension_name"))
        dimension_value = _str_or_none(finding.get("dimension_value"))
        contribution_pp = _float_or_none(finding.get("contribution_pp"))
        delta_pp = _float_or_none(finding.get("delta_pp"))
    elif finding_type == "segment_stability":
        dimension_name = _str_or_none(finding.get("dimension_name"))
        dimension_value = _str_or_none(finding.get("dimension_value"))
        delta_pp = _float_or_none(
            finding.get("delta_pp")
            or _metric_delta(finding.get("current_metric_value"), finding.get("baseline_metric_value"))
        )
    elif finding_type == "metric_monitor":
        sev = finding.get("severity")
        severity = sev if isinstance(sev, str) else (sev.value if hasattr(sev, "value") else None)
        delta_pp = _float_or_none(finding.get("delta_pp"))
    elif finding_type == "trend_analysis":
        delta_pp = _float_or_none(finding.get("rolling_change_pp"))
    elif finding_type == "strategy_impact":
        delta_pp = _float_or_none(finding.get("fpd7_delta_pp"))
        dimension_name = "strategy"
        dimension_value = _str_or_none(finding.get("strategy_name"))
        approval_delta_pp = _float_or_none(finding.get("approval_delta_pp"))
        volume_delta_pct = _float_or_none(finding.get("volume_delta_pct"))

    generated_raw = finding.get("generated_at")
    if isinstance(generated_raw, datetime):
        generated_at = generated_raw
    elif isinstance(generated_raw, str):
        generated_at = datetime.fromisoformat(generated_raw.replace("Z", "+00:00"))
    else:
        generated_at = datetime.now(timezone.utc)

    return StoredFinding(
        finding_id=str(finding.get("finding_id") or uuid4()),
        investigation_id=investigation_id,
        metric_name=resolved_metric,
        finding_type=finding_type,
        dimension_name=dimension_name,
        dimension_value=dimension_value,
        summary=str(finding.get("summary", "")),
        severity=severity,
        contribution_pp=contribution_pp,
        delta_pp=delta_pp,
        approval_delta_pp=approval_delta_pp,
        volume_delta_pct=volume_delta_pct,
        generated_at=generated_at,
    )


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _metric_delta(current: object, baseline: object) -> float | None:
    if current is None or baseline is None:
        return None
    return float(current) - float(baseline)
