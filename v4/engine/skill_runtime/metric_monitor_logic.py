"""Pure functions for metric monitor — imported only by MetricMonitorSkill.run."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from models.metric_monitor import (
    AttributionHint,
    InvestigationGate,
    InvestigationTrigger,
    MetricDirection,
    MetricMonitorFinding,
    Severity,
)
from models.metric_profiles import MetricProfile, MetricThresholds


@dataclass(frozen=True)
class InvestigationDecision:
    gate: InvestigationGate
    needs_investigation: bool
    triggers: list[InvestigationTrigger]
    consecutive_weeks_trend: bool


def period_mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot compute mean of empty values")
    return float(sum(values) / len(values))


def compute_delta(
    current_avg: float, previous_avg: float
) -> tuple[float, float | None]:
    delta_pp = round((current_avg - previous_avg) * 100, 2)
    if previous_avg == 0:
        return delta_pp, None
    change_rate = round((current_avg - previous_avg) / previous_avg, 4)
    return delta_pp, change_rate


def compute_direction(delta_pp: float) -> MetricDirection:
    if delta_pp > 0:
        return MetricDirection.UP
    if delta_pp < 0:
        return MetricDirection.DOWN
    return MetricDirection.FLAT


def prior_prior_window(
    previous_start_date: date, previous_end_date: date
) -> tuple[date, date]:
    length_days = (previous_end_date - previous_start_date).days + 1
    prior_end = previous_start_date - timedelta(days=1)
    prior_start = prior_end - timedelta(days=length_days - 1)
    return prior_start, prior_end


def is_consecutive_same_direction(delta_current: float, delta_prior: float) -> bool:
    if delta_current == 0 or delta_prior == 0:
        return False
    return (delta_current > 0 and delta_prior > 0) or (
        delta_current < 0 and delta_prior < 0
    )


def evaluate_investigation(
    thresholds: MetricThresholds,
    delta_pp: float,
    prior_delta_pp: float | None,
) -> InvestigationDecision:
    abs_delta = abs(delta_pp)
    triggers: list[InvestigationTrigger] = []
    consecutive = False

    if thresholds.consecutive_enabled and prior_delta_pp is not None:
        consecutive = is_consecutive_same_direction(delta_pp, prior_delta_pp)
        if consecutive:
            if thresholds.profile == MetricProfile.LONG_TERM_RISK:
                cumulative = abs(delta_pp) + abs(prior_delta_pp)
                if (
                    thresholds.consecutive_cumulative_pp is not None
                    and cumulative >= thresholds.consecutive_cumulative_pp
                ):
                    triggers.append(InvestigationTrigger.CONSECUTIVE_WEEKS_CUMULATIVE)
            else:
                triggers.append(InvestigationTrigger.CONSECUTIVE_WEEKS_TREND)

    if abs_delta >= thresholds.investigate_pp:
        if InvestigationTrigger.SINGLE_PERIOD_THRESHOLD not in triggers:
            triggers.append(InvestigationTrigger.SINGLE_PERIOD_THRESHOLD)

    needs = len(triggers) > 0
    if needs:
        gate = InvestigationGate.INVESTIGATE
    elif thresholds.profile == MetricProfile.APPROVAL_RATE and abs_delta >= 1.0:
        gate = InvestigationGate.WATCH
    elif (
        thresholds.profile == MetricProfile.LONG_TERM_RISK
        and abs_delta >= thresholds.skip_pp * 0.75
    ):
        gate = InvestigationGate.WATCH
    else:
        gate = InvestigationGate.SKIP

    return InvestigationDecision(
        gate=gate,
        needs_investigation=needs,
        triggers=triggers,
        consecutive_weeks_trend=consecutive,
    )


def compute_severity(
    thresholds: MetricThresholds,
    abs_delta_pp: float,
    *,
    consecutive_weeks_trend: bool,
    needs_investigation: bool,
) -> Severity:
    if not needs_investigation and abs_delta_pp < thresholds.severity_medium_pp:
        return Severity.LOW

    if thresholds.profile == MetricProfile.SHORT_TERM_RISK:
        if abs_delta_pp > thresholds.severity_high_pp or (
            consecutive_weeks_trend and needs_investigation
        ):
            return Severity.HIGH
        if abs_delta_pp >= thresholds.severity_medium_pp:
            return Severity.MEDIUM
        return Severity.LOW

    if thresholds.profile == MetricProfile.APPROVAL_RATE:
        if abs_delta_pp >= thresholds.severity_high_pp:
            return Severity.HIGH
        if abs_delta_pp >= thresholds.severity_medium_pp:
            return Severity.MEDIUM
        return Severity.LOW

    if abs_delta_pp >= thresholds.severity_high_pp:
        return Severity.HIGH
    if abs_delta_pp >= thresholds.severity_medium_pp:
        return Severity.MEDIUM
    return Severity.LOW


def resolve_attribution_hint(
    direction: MetricDirection,
    *,
    risk_up_is_bad: bool = True,
    consecutive_weeks_trend: bool = False,
) -> AttributionHint:
    if direction == MetricDirection.FLAT and not consecutive_weeks_trend:
        return AttributionHint.NEUTRAL

    if consecutive_weeks_trend:
        if direction == MetricDirection.UP:
            worsening = risk_up_is_bad
        elif direction == MetricDirection.DOWN:
            worsening = False
        else:
            return AttributionHint.NEUTRAL
    else:
        worsening = (direction == MetricDirection.UP) if risk_up_is_bad else (
            direction == MetricDirection.DOWN
        )

    if worsening:
        return AttributionHint.RISK_DETERIORATION
    return AttributionHint.RISK_IMPROVEMENT


def _trigger_labels(triggers: list[InvestigationTrigger]) -> str:
    labels = {
        InvestigationTrigger.SINGLE_PERIOD_THRESHOLD: "单周阈值",
        InvestigationTrigger.CONSECUTIVE_WEEKS_TREND: "连续两周同向",
        InvestigationTrigger.CONSECUTIVE_WEEKS_CUMULATIVE: "连续两周累计超阈",
    }
    return "、".join(labels[t] for t in triggers) if triggers else "无"


def build_finding(
    *,
    metric_name: str,
    metric_profile: MetricProfile,
    thresholds: MetricThresholds,
    current_value: float,
    previous_value: float,
    delta_pp: float,
    prior_period_delta_pp: float | None,
    change_rate: float | None,
    direction: MetricDirection,
    investigation_gate: InvestigationGate,
    needs_investigation: bool,
    severity: Severity,
    attribution_hint: AttributionHint,
    consecutive_weeks_trend: bool,
    investigation_triggers: list[InvestigationTrigger],
    current_start_date: date,
    current_end_date: date,
    previous_start_date: date,
    previous_end_date: date,
) -> MetricMonitorFinding:
    cur_pct = current_value * 100
    prev_pct = previous_value * 100
    gate_label = {
        InvestigationGate.SKIP: "无需分析",
        InvestigationGate.WATCH: "观察",
        InvestigationGate.INVESTIGATE: "需发起归因",
    }[investigation_gate]
    profile_label = {
        MetricProfile.SHORT_TERM_RISK: "短期风险",
        MetricProfile.APPROVAL_RATE: "通过率",
        MetricProfile.LONG_TERM_RISK: "长期风险",
    }[metric_profile]
    change_txt = f"{delta_pp:+.2f}pp"
    if change_rate is not None:
        change_txt += f"（相对变化 {change_rate:+.2%}）"

    prior_txt = ""
    if prior_period_delta_pp is not None:
        prior_txt = f"，前一周环比 {prior_period_delta_pp:+.2f}pp"
    trend_txt = ""
    if consecutive_weeks_trend:
        trend_txt = "，连续两周同向波动"

    summary = (
        f"指标 {metric_name}（{profile_label}）：当前周期（{current_start_date} ~ {current_end_date}）"
        f"均值 {cur_pct:.2f}%，对比周期（{previous_start_date} ~ {previous_end_date}）"
        f"均值 {prev_pct:.2f}%，变化 {change_txt}{prior_txt}{trend_txt}，"
        f"方向 {direction.value}，归因意图 {attribution_hint.value}，"
        f"触发 {_trigger_labels(investigation_triggers)}，{gate_label}，严重度 {severity.value}。"
    )
    generated_at = datetime.now(timezone.utc)
    evidence = {
        "metric_profile": metric_profile.value,
        "current_value": round(current_value, 6),
        "previous_value": round(previous_value, 6),
        "delta_pp": delta_pp,
        "prior_period_delta_pp": prior_period_delta_pp,
        "change_rate": change_rate,
        "direction": direction.value,
        "investigation_gate": investigation_gate.value,
        "needs_investigation": needs_investigation,
        "severity": severity.value,
        "consecutive_weeks_trend": consecutive_weeks_trend,
        "investigation_triggers": [t.value for t in investigation_triggers],
        "attribution_hint": attribution_hint.value,
        "current_period": {
            "start_date": current_start_date.isoformat(),
            "end_date": current_end_date.isoformat(),
        },
        "previous_period": {
            "start_date": previous_start_date.isoformat(),
            "end_date": previous_end_date.isoformat(),
        },
    }
    return MetricMonitorFinding(
        finding_type="metric_monitor",
        metric_name=metric_name,
        summary=summary,
        evidence=evidence,
        generated_at=generated_at,
        metric_profile=metric_profile,
        current_value=round(current_value, 6),
        previous_value=round(previous_value, 6),
        delta_pp=delta_pp,
        prior_period_delta_pp=prior_period_delta_pp,
        change_rate=change_rate,
        direction=direction,
        investigation_gate=investigation_gate,
        needs_investigation=needs_investigation,
        is_abnormal=needs_investigation,
        severity=severity,
        consecutive_weeks_trend=consecutive_weeks_trend,
        investigation_triggers=investigation_triggers,
        attribution_hint=attribution_hint,
    )
