"""确定性 segment 稳定性算法（纯计算，无 DB / workflow / logging）。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass(frozen=True)
class StabilityEngineConfig:
    cv_low: float = 0.08
    cv_high: float = 0.18
    slope_threshold: float = 0.00015
    regime_shift_rate_threshold: float = 0.005
    consecutive_deterioration_min: int = 4
    stability_healthy_min: float = 0.7
    recent_period_fraction: float = 0.25
    recent_period_min: int = 2


@dataclass(frozen=True)
class VolatilityResult:
    volatility_score: float
    volatility_level: str
    std: float
    rolling_std: float
    coefficient_of_variation: float


@dataclass(frozen=True)
class RegimeShiftResult:
    regime_shift_detected: bool
    recent_mean: float
    historical_mean: float
    shift_delta: float


@dataclass(frozen=True)
class StabilityEngineOutput:
    stability_score: float
    volatility_score: float
    volatility_level: str
    trend_direction: str
    consecutive_up_periods: int
    regime_shift_detected: bool
    segment_health: str
    current_metric_value: float
    baseline_metric_value: float
    summary: str


class StabilityEngine:
    """对单 segment 时间序列做波动性、稳定性、趋势与 regime shift 分析。"""

    def __init__(self, config: StabilityEngineConfig | None = None) -> None:
        self._config = config or StabilityEngineConfig()

    def analyze(
        self,
        *,
        metric_name: str,
        dimension_name: str,
        dimension_value: str,
        period_labels: list[str],
        values: list[float],
        rolling_window_periods: int = 3,
        recent_window_periods: int | None = None,
    ) -> StabilityEngineOutput:
        if len(values) != len(period_labels):
            raise ValueError("period_labels 与 values 长度须一致")
        if len(values) < 2:
            raise ValueError("稳定性分析至少需要 2 个观测点")

        vol = self.calculate_volatility(values, rolling_window_periods)
        stability = self.calculate_stability_score(vol.coefficient_of_variation)
        trend = self.classify_trend_direction(values)
        consecutive = self.analyze_consecutive_deterioration(values)
        recent_n = recent_window_periods or self._recent_window_size(len(values))
        regime = self.detect_regime_shift(values, recent_periods=recent_n)
        health = self.classify_segment_health(
            stability_score=stability,
            volatility_level=vol.volatility_level,
            consecutive_up_periods=consecutive,
            regime_shift_detected=regime.regime_shift_detected,
            trend_direction=trend,
        )
        current = values[-1]
        baseline = regime.historical_mean
        summary = self.build_summary(
            metric_name=metric_name,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            window_periods=len(values),
            stability_score=stability,
            volatility_level=vol.volatility_level,
            trend_direction=trend,
            consecutive_up=consecutive,
            regime_shift_detected=regime.regime_shift_detected,
            segment_health=health,
            current_metric_value=current,
            baseline_metric_value=baseline,
        )

        return StabilityEngineOutput(
            stability_score=round(stability, 4),
            volatility_score=round(vol.volatility_score, 6),
            volatility_level=vol.volatility_level,
            trend_direction=trend,
            consecutive_up_periods=consecutive,
            regime_shift_detected=regime.regime_shift_detected,
            segment_health=health,
            current_metric_value=round(current, 6),
            baseline_metric_value=round(baseline, 6),
            summary=summary,
        )

    def calculate_volatility(
        self,
        values: list[float],
        rolling_window: int = 3,
    ) -> VolatilityResult:
        std = pstdev(values) if len(values) >= 2 else 0.0
        avg = mean(values)
        cv = self.coefficient_of_variation(std, avg)
        roll = self.rolling_std(values, rolling_window)
        rolling_std = roll[-1] if roll else 0.0
        level = self.classify_volatility_level(cv)
        return VolatilityResult(
            volatility_score=cv,
            volatility_level=level,
            std=std,
            rolling_std=rolling_std,
            coefficient_of_variation=cv,
        )

    def calculate_stability_score(self, coefficient_of_variation: float) -> float:
        """越稳定分数越高，范围 [0, 1]。"""
        cfg = self._config
        if math.isinf(coefficient_of_variation):
            return 0.0
        if coefficient_of_variation <= 0:
            return 1.0
        normalized = coefficient_of_variation / (cfg.cv_high * 2)
        return max(0.0, min(1.0, 1.0 - normalized))

    def detect_regime_shift(
        self,
        values: list[float],
        *,
        recent_periods: int,
    ) -> RegimeShiftResult:
        n = len(values)
        recent_n = min(max(1, recent_periods), n - 1) if n > 1 else 1
        recent = values[-recent_n:]
        historical = values[:-recent_n] if n > recent_n else values[:1]
        recent_mean = mean(recent)
        historical_mean = mean(historical)
        shift = recent_mean - historical_mean
        detected = (
            shift > self._config.regime_shift_rate_threshold
            and recent_mean > historical_mean
        )
        return RegimeShiftResult(
            regime_shift_detected=detected,
            recent_mean=recent_mean,
            historical_mean=historical_mean,
            shift_delta=shift,
        )

    def analyze_consecutive_deterioration(self, values: list[float]) -> int:
        """从最近一期向前统计连续环比上涨期数。"""
        if len(values) < 2:
            return 0
        streak = 0
        for i in range(len(values) - 1, 0, -1):
            if values[i] > values[i - 1]:
                streak += 1
            else:
                break
        return streak

    def classify_segment_health(
        self,
        *,
        stability_score: float,
        volatility_level: str,
        consecutive_up_periods: int,
        regime_shift_detected: bool,
        trend_direction: str,
    ) -> str:
        cfg = self._config

        if volatility_level == "high" and regime_shift_detected:
            return "unstable"
        if consecutive_up_periods >= cfg.consecutive_deterioration_min:
            return "deteriorating"
        if (
            stability_score >= cfg.stability_healthy_min
            and volatility_level == "low"
            and not regime_shift_detected
            and consecutive_up_periods < 2
            and trend_direction != "upward"
        ):
            return "healthy"
        if volatility_level == "medium":
            return "watchlist"
        if volatility_level == "high" or stability_score < 0.4:
            return "unstable"
        if trend_direction == "upward" and consecutive_up_periods >= 2:
            return "deteriorating"
        return "watchlist"

    def classify_trend_direction(self, values: list[float]) -> str:
        slope = self._linear_slope(values)
        threshold = self._config.slope_threshold
        if slope > threshold:
            return "upward"
        if slope < -threshold:
            return "downward"
        return "stable"

    def classify_volatility_level(self, cv: float) -> str:
        cfg = self._config
        if cv < cfg.cv_low:
            return "low"
        if cv < cfg.cv_high:
            return "medium"
        return "high"

    @staticmethod
    def coefficient_of_variation(std: float, avg: float) -> float:
        if avg == 0:
            return 0.0 if std == 0 else float("inf")
        return abs(std / avg)

    @staticmethod
    def rolling_std(values: list[float], window: int) -> list[float]:
        if window < 1:
            raise ValueError("window 须 >= 1")
        out: list[float] = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            segment = values[start : i + 1]
            if len(segment) < 2:
                out.append(0.0)
            else:
                out.append(pstdev(segment))
        return out

    def _recent_window_size(self, n: int) -> int:
        cfg = self._config
        by_fraction = max(cfg.recent_period_min, math.ceil(n * cfg.recent_period_fraction))
        return min(by_fraction, n - 1) if n > 1 else 1

    @staticmethod
    def _linear_slope(values: list[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = mean(values)
        num = 0.0
        den = 0.0
        for i, y in enumerate(values):
            dx = i - x_mean
            dy = y - y_mean
            num += dx * dy
            den += dx * dx
        if den == 0:
            return 0.0
        return num / den

    def build_summary(
        self,
        *,
        metric_name: str,
        dimension_name: str,
        dimension_value: str,
        window_periods: int,
        stability_score: float,
        volatility_level: str,
        trend_direction: str,
        consecutive_up: int,
        regime_shift_detected: bool,
        segment_health: str,
        current_metric_value: float,
        baseline_metric_value: float,
    ) -> str:
        metric = metric_name.upper()
        seg = f"{dimension_name}={dimension_value}"
        health_cn = {
            "healthy": "健康",
            "watchlist": "观察",
            "deteriorating": "持续恶化",
            "unstable": "不稳定",
        }[segment_health]
        trend_cn = {"upward": "上升", "downward": "下降", "stable": "平稳"}[trend_direction]
        vol_cn = {"low": "低", "medium": "中", "high": "高"}[volatility_level]

        parts = [
            f"{seg} 在近 {window_periods} 期 {metric} 稳定性评分为 {stability_score:.2f}（{health_cn}）",
            f"波动性{vol_cn}",
            f"风险趋势{trend_cn}",
        ]
        if consecutive_up >= 2:
            parts.append(f"连续 {consecutive_up} 期环比上涨")
        if regime_shift_detected:
            parts.append("近期相对历史基线出现显著恶化")
        cur_pp = round(current_metric_value * 100, 2)
        base_pp = round(baseline_metric_value * 100, 2)
        parts.append(f"当前值 {cur_pp}% vs 历史基线 {base_pp}%")
        return "，".join(parts) + "。"

    @staticmethod
    def rolling_window_for_days(window_days: int, aggregation_level: str) -> int:
        if aggregation_level == "day":
            return max(1, window_days)
        if aggregation_level == "week":
            return max(1, math.ceil(window_days / 7))
        raise ValueError(f"不支持的 aggregation_level: {aggregation_level}")

    @staticmethod
    def recent_window_for_days(recent_days: int, aggregation_level: str) -> int:
        return StabilityEngine.rolling_window_for_days(recent_days, aggregation_level)
