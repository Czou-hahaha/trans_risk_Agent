"""确定性策略影响算法（纯计算，无 DB / workflow / logging / LLM）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


RATE_METRICS = frozenset({"approval_rate", "fpd7", "rule_hit_rate"})
VOLUME_METRICS = frozenset({"volume", "loan_amount", "gmv"})
DEFAULT_METRICS = ("approval_rate", "fpd7", "volume")


@dataclass(frozen=True)
class StrategyImpactEngineConfig:
    neutral_fpd7_pp: float = 0.15
    neutral_approval_pp: float = 0.5
    neutral_volume_pct: float = 2.0

    min_risk_improvement_pp: float = 0.3
    significant_fpd7_improvement_pp: float = 0.5
    strong_fpd7_improvement_pp: float = 0.8
    limited_risk_improvement_pp: float = 0.5

    small_approval_loss_pp: float = 1.5
    acceptable_approval_loss_pp: float = 2.0
    large_approval_loss_pp: float = 3.0

    acceptable_volume_loss_pct: float = 5.0
    large_volume_loss_pct: float = 8.0

    min_approval_loss_for_efficiency: float = 0.01
    min_volume_loss_for_efficiency: float = 0.01


@dataclass(frozen=True)
class DailyMetricObservation:
    event_date: date
    metric_name: str
    metric_value: float
    sample_size: int = 1


@dataclass(frozen=True)
class BeforeAfterMetrics:
    before: dict[str, float]
    after: dict[str, float]
    before_total_samples: dict[str, int]
    after_total_samples: dict[str, int]


@dataclass(frozen=True)
class MetricDelta:
    metric_name: str
    before: float
    after: float
    absolute_delta: float
    delta_pp: float | None
    delta_pct: float | None


@dataclass(frozen=True)
class StrategyImpactEngineOutput:
    approval_rate_before: float
    approval_rate_after: float
    approval_delta_pp: float
    fpd7_before: float
    fpd7_after: float
    fpd7_delta_pp: float
    volume_before: float
    volume_after: float
    volume_delta_pct: float
    risk_reduction_efficiency: float
    strategy_effectiveness: str
    summary: str
    metric_deltas: dict[str, MetricDelta]


class StrategyImpactEngine:
    """策略上线前后指标对比、tradeoff 与有效性分类（纯算法）。"""

    def __init__(self, config: StrategyImpactEngineConfig | None = None) -> None:
        self._config = config or StrategyImpactEngineConfig()

    def analyze(
        self,
        *,
        strategy_name: str,
        deployment_date: date,
        observations: list[DailyMetricObservation],
        before_window_days: int = 14,
        after_window_days: int = 14,
        metrics: tuple[str, ...] | list[str] | None = None,
    ) -> StrategyImpactEngineOutput:
        metric_names = tuple(metrics) if metrics else DEFAULT_METRICS
        before_after = self.aggregate_before_after_metrics(
            observations=observations,
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
            metric_names=metric_names,
        )

        deltas: dict[str, MetricDelta] = {}
        for name in metric_names:
            before_val = before_after.before.get(name)
            after_val = before_after.after.get(name)
            if before_val is None or after_val is None:
                raise ValueError(f"指标 {name!r} 在 before/after 窗口内数据不足")
            deltas[name] = self.calculate_metric_delta(name, before_val, after_val)

        approval = deltas["approval_rate"]
        fpd7 = deltas["fpd7"]
        volume = deltas["volume"]

        efficiency = self.calculate_tradeoff_efficiency(
            fpd7_delta_pp=fpd7.delta_pp or 0.0,
            approval_delta_pp=approval.delta_pp or 0.0,
            volume_delta_pct=volume.delta_pct or 0.0,
        )
        effectiveness = self.classify_strategy_effectiveness(
            fpd7_delta_pp=fpd7.delta_pp or 0.0,
            approval_delta_pp=approval.delta_pp or 0.0,
            volume_delta_pct=volume.delta_pct or 0.0,
        )
        summary = self.generate_deterministic_summary(
            strategy_name=strategy_name,
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
            fpd7_delta_pp=fpd7.delta_pp or 0.0,
            approval_delta_pp=approval.delta_pp or 0.0,
            volume_delta_pct=volume.delta_pct or 0.0,
            risk_reduction_efficiency=efficiency,
            strategy_effectiveness=effectiveness,
        )

        return StrategyImpactEngineOutput(
            approval_rate_before=round(approval.before, 6),
            approval_rate_after=round(approval.after, 6),
            approval_delta_pp=round(approval.delta_pp or 0.0, 2),
            fpd7_before=round(fpd7.before, 6),
            fpd7_after=round(fpd7.after, 6),
            fpd7_delta_pp=round(fpd7.delta_pp or 0.0, 2),
            volume_before=round(volume.before, 6),
            volume_after=round(volume.after, 6),
            volume_delta_pct=round(volume.delta_pct or 0.0, 2),
            risk_reduction_efficiency=efficiency,
            strategy_effectiveness=effectiveness,
            summary=summary,
            metric_deltas=deltas,
        )

    def aggregate_before_after_metrics(
        self,
        *,
        observations: list[DailyMetricObservation],
        deployment_date: date,
        before_window_days: int,
        after_window_days: int,
        metric_names: tuple[str, ...] | list[str],
    ) -> BeforeAfterMetrics:
        if before_window_days < 1 or after_window_days < 1:
            raise ValueError("before_window_days 与 after_window_days 须 >= 1")

        from datetime import timedelta

        before_start = deployment_date - timedelta(days=before_window_days)
        before_end = deployment_date - timedelta(days=1)
        after_start = deployment_date
        after_end = deployment_date + timedelta(days=after_window_days - 1)

        before_buckets: dict[str, list[tuple[float, int]]] = {
            m: [] for m in metric_names
        }
        after_buckets: dict[str, list[tuple[float, int]]] = {
            m: [] for m in metric_names
        }

        for obs in observations:
            if obs.metric_name not in before_buckets:
                continue
            if before_start <= obs.event_date <= before_end:
                before_buckets[obs.metric_name].append(
                    (obs.metric_value, max(1, obs.sample_size))
                )
            elif after_start <= obs.event_date <= after_end:
                after_buckets[obs.metric_name].append(
                    (obs.metric_value, max(1, obs.sample_size))
                )

        before: dict[str, float] = {}
        after: dict[str, float] = {}
        before_samples: dict[str, int] = {}
        after_samples: dict[str, int] = {}

        for name in metric_names:
            b_vals = before_buckets[name]
            a_vals = after_buckets[name]
            if not b_vals or not a_vals:
                continue
            before[name] = self._weighted_mean(b_vals)
            after[name] = self._weighted_mean(a_vals)
            before_samples[name] = sum(s for _, s in b_vals)
            after_samples[name] = sum(s for _, s in a_vals)

        return BeforeAfterMetrics(
            before=before,
            after=after,
            before_total_samples=before_samples,
            after_total_samples=after_samples,
        )

    def calculate_metric_delta(
        self,
        metric_name: str,
        before: float,
        after: float,
    ) -> MetricDelta:
        absolute_delta = after - before
        delta_pp: float | None = None
        delta_pct: float | None = None

        if metric_name in RATE_METRICS:
            delta_pp = round(absolute_delta * 100, 2)
        elif metric_name in VOLUME_METRICS:
            if before == 0:
                delta_pct = 0.0 if after == 0 else 100.0
            else:
                delta_pct = round((absolute_delta / before) * 100, 2)
        else:
            if before == 0:
                delta_pct = 0.0 if after == 0 else 100.0
            else:
                delta_pct = round((absolute_delta / before) * 100, 2)
            delta_pp = round(absolute_delta * 100, 2)

        return MetricDelta(
            metric_name=metric_name,
            before=before,
            after=after,
            absolute_delta=round(absolute_delta, 6),
            delta_pp=delta_pp,
            delta_pct=delta_pct,
        )

    def calculate_tradeoff_efficiency(
        self,
        *,
        fpd7_delta_pp: float,
        approval_delta_pp: float,
        volume_delta_pct: float,
    ) -> float:
        """风险改善效率：每损失 1pp 通过率带来的 FPD7 下降（pp）。"""
        cfg = self._config
        fpd7_reduction = max(0.0, -fpd7_delta_pp)
        approval_loss = max(0.0, -approval_delta_pp)
        volume_loss = max(0.0, -volume_delta_pct)

        if approval_loss >= cfg.min_approval_loss_for_efficiency:
            return round(fpd7_reduction / approval_loss, 4)
        if volume_loss >= cfg.min_volume_loss_for_efficiency:
            return round(fpd7_reduction / volume_loss, 4)
        return round(fpd7_reduction, 4)

    def classify_strategy_effectiveness(
        self,
        *,
        fpd7_delta_pp: float,
        approval_delta_pp: float,
        volume_delta_pct: float,
    ) -> str:
        cfg = self._config

        if (
            abs(fpd7_delta_pp) < cfg.neutral_fpd7_pp
            and abs(approval_delta_pp) < cfg.neutral_approval_pp
            and abs(volume_delta_pct) < cfg.neutral_volume_pct
        ):
            return "neutral"

        approval_loss = max(0.0, -approval_delta_pp)
        volume_loss = max(0.0, -volume_delta_pct)
        fpd7_improved = fpd7_delta_pp <= -cfg.min_risk_improvement_pp
        fpd7_strong = fpd7_delta_pp <= -cfg.significant_fpd7_improvement_pp
        fpd7_very_strong = fpd7_delta_pp <= -cfg.strong_fpd7_improvement_pp

        if not fpd7_improved:
            return "ineffective"

        small_business = (
            approval_loss <= cfg.small_approval_loss_pp
            and volume_loss <= cfg.acceptable_volume_loss_pct * 0.6
        )
        acceptable_business = (
            approval_loss <= cfg.acceptable_approval_loss_pp
            and volume_loss <= cfg.acceptable_volume_loss_pct
        )
        large_business = (
            approval_loss >= cfg.large_approval_loss_pp
            or volume_loss >= cfg.large_volume_loss_pct
        )
        limited_risk_gain = fpd7_delta_pp > -cfg.significant_fpd7_improvement_pp

        if fpd7_very_strong and small_business:
            return "highly_effective"
        if large_business and limited_risk_gain:
            return "over_tightened"
        if fpd7_improved and acceptable_business:
            return "effective"
        if fpd7_strong:
            return "effective"
        return "ineffective"

    def generate_deterministic_summary(
        self,
        *,
        strategy_name: str,
        deployment_date: date,
        before_window_days: int,
        after_window_days: int,
        fpd7_delta_pp: float,
        approval_delta_pp: float,
        volume_delta_pct: float,
        risk_reduction_efficiency: float,
        strategy_effectiveness: str,
    ) -> str:
        eff_cn = {
            "highly_effective": "高度有效",
            "effective": "有效",
            "over_tightened": "过度收紧",
            "ineffective": "无效",
            "neutral": "影响中性",
        }[strategy_effectiveness]

        def _fmt_pp(delta: float, label: str, lower_is_better: bool) -> str:
            sign = "+" if delta >= 0 else ""
            direction = "下降" if delta < 0 else "上升" if delta > 0 else "持平"
            if lower_is_better and delta < 0:
                direction = "改善（下降）"
            elif lower_is_better and delta > 0:
                direction = "恶化（上升）"
            elif not lower_is_better and delta < 0:
                direction = "下降"
            return f"{label}{direction} {sign}{delta}pp"

        parts = [
            f"策略 {strategy_name}（上线日 {deployment_date.isoformat()}，"
            f"前 {before_window_days} 天 vs 后 {after_window_days} 天）",
            _fmt_pp(fpd7_delta_pp, "FPD7 ", lower_is_better=True),
            _fmt_pp(approval_delta_pp, "通过率 ", lower_is_better=False),
            f"业务量变动 {volume_delta_pct:+.1f}%",
            f"风险改善效率 {risk_reduction_efficiency:.2f}",
            f"综合判定：{eff_cn}",
        ]

        if strategy_effectiveness == "highly_effective":
            parts.append("风险显著改善且业务影响可控，策略收紧性价比高")
        elif strategy_effectiveness == "effective":
            parts.append("风险改善与通过率/流量损失处于可接受 tradeoff")
        elif strategy_effectiveness == "over_tightened":
            parts.append("通过率或流量损失偏大而风险改善有限，存在过度收紧")
        elif strategy_effectiveness == "ineffective":
            parts.append("未观察到实质风险改善，策略效果存疑")
        else:
            parts.append("上线前后核心指标波动均在噪声范围内")

        return "，".join(parts) + "。"

    @staticmethod
    def _weighted_mean(pairs: list[tuple[float, int]]) -> float:
        total_w = sum(w for _, w in pairs)
        if total_w == 0:
            return 0.0
        return sum(v * w for v, w in pairs) / total_w
