"""确定性时序趋势算法（纯计算，无 DB / workflow）。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass(frozen=True)
class TrendEngineConfig:
    slope_threshold: float = 0.00015
    slope_strong: float = 0.0004
    rolling_change_weak_pp: float = 0.5
    rolling_change_moderate_pp: float = 1.5
    rolling_change_strong_pp: float = 2.5
    consecutive_weak: int = 2
    consecutive_moderate: int = 3
    consecutive_strong: int = 4
    cv_low: float = 0.08
    cv_high: float = 0.18
    peak_z_threshold: float = 2.0


@dataclass(frozen=True)
class TrendEngineOutput:
    trend_direction: str
    trend_strength: str
    rolling_change_pp: float
    slope_value: float
    volatility_score: float
    volatility_level: str
    consecutive_up_periods: int
    anomaly_periods: list[str]
    current_value: float
    baseline_value: float
    summary: str


class TrendEngine:
    """对数值时间序列做确定性趋势分析。"""

    def __init__(self, config: TrendEngineConfig | None = None) -> None:
        self._config = config or TrendEngineConfig()

    def analyze(
        self,
        *,
        metric_name: str,
        period_labels: list[str],
        values: list[float],
        rolling_window_periods: int,
        baseline_window_periods: int,
    ) -> TrendEngineOutput:
        if len(values) != len(period_labels):
            raise ValueError("period_labels 与 values 长度须一致")
        if len(values) < 2:
            raise ValueError("趋势分析至少需要 2 个观测点")

        rolling = self.rolling_average(values, rolling_window_periods)
        baseline = self.rolling_average(values, baseline_window_periods)
        current_value = rolling[-1]
        baseline_value = baseline[0] if len(baseline) > 1 else baseline[-1]
        rolling_change_pp = round((current_value - baseline_value) * 100, 2)

        slope = self.calculate_linear_slope(values)
        direction = self.classify_direction(slope)
        consecutive = self.count_consecutive_up(values)
        vol_score, vol_level = self.volatility_metrics(values)
        anomalies = self.detect_peak_periods(values, period_labels)

        strength = self.classify_strength(
            slope=slope,
            rolling_change_pp=rolling_change_pp,
            consecutive_up=consecutive,
        )
        summary = self.build_summary(
            metric_name=metric_name,
            direction=direction,
            strength=strength,
            rolling_change_pp=rolling_change_pp,
            consecutive_up=consecutive,
            volatility_level=vol_level,
        )

        return TrendEngineOutput(
            trend_direction=direction,
            trend_strength=strength,
            rolling_change_pp=rolling_change_pp,
            slope_value=round(slope, 8),
            volatility_score=round(vol_score, 6),
            volatility_level=vol_level,
            consecutive_up_periods=consecutive,
            anomaly_periods=anomalies,
            current_value=round(current_value, 6),
            baseline_value=round(baseline_value, 6),
            summary=summary,
        )

    def rolling_average(self, values: list[float], window: int) -> list[float]:
        if window < 1:
            raise ValueError("window 须 >= 1")
        n = len(values)
        out: list[float] = []
        for i in range(n):
            start = max(0, i - window + 1)
            segment = values[start : i + 1]
            out.append(mean(segment))
        return out

    def calculate_linear_slope(self, values: list[float]) -> float:
        """对索引 0..n-1 做最小二乘斜率。"""
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

    def count_consecutive_up(self, values: list[float]) -> int:
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

    def volatility_metrics(self, values: list[float]) -> tuple[float, str]:
        if len(values) < 2:
            return 0.0, "low"
        std = pstdev(values)
        avg = mean(values)
        cv = self.coefficient_of_variation(std, avg)
        level = self.classify_volatility(cv)
        return cv, level

    @staticmethod
    def coefficient_of_variation(std: float, avg: float) -> float:
        if avg == 0:
            return 0.0 if std == 0 else float("inf")
        return abs(std / avg)

    def classify_volatility(self, cv: float) -> str:
        cfg = self._config
        if cv < cfg.cv_low:
            return "low"
        if cv < cfg.cv_high:
            return "medium"
        return "high"

    def classify_direction(self, slope: float) -> str:
        threshold = self._config.slope_threshold
        if slope > threshold:
            return "upward"
        if slope < -threshold:
            return "downward"
        return "stable"

    def classify_strength(
        self,
        *,
        slope: float,
        rolling_change_pp: float,
        consecutive_up: int,
    ) -> str:
        cfg = self._config
        abs_change = abs(rolling_change_pp)
        abs_slope = abs(slope)

        strong_signals = 0
        moderate_signals = 0

        if abs_change >= cfg.rolling_change_strong_pp:
            strong_signals += 1
        elif abs_change >= cfg.rolling_change_moderate_pp:
            moderate_signals += 1

        if abs_slope >= cfg.slope_strong:
            strong_signals += 1
        elif abs_slope >= cfg.slope_threshold * 2:
            moderate_signals += 1

        if consecutive_up >= cfg.consecutive_strong:
            strong_signals += 1
        elif consecutive_up >= cfg.consecutive_moderate:
            moderate_signals += 1
        elif consecutive_up >= cfg.consecutive_weak:
            moderate_signals += 1

        if strong_signals >= 2 or (strong_signals >= 1 and moderate_signals >= 1):
            return "strong"
        if strong_signals >= 1 or moderate_signals >= 2:
            return "moderate"
        if moderate_signals >= 1 or abs_change >= cfg.rolling_change_weak_pp:
            return "weak"
        return "weak"

    def detect_peak_periods(
        self,
        values: list[float],
        period_labels: list[str],
    ) -> list[str]:
        """留一法：当期值高于其余期均值 + z·σ 则记为异常波峰。"""
        if len(values) < 3:
            return []
        peaks: list[str] = []
        z = self._config.peak_z_threshold
        for i, (label, value) in enumerate(zip(period_labels, values, strict=True)):
            others = [v for j, v in enumerate(values) if j != i]
            if len(others) < 2:
                continue
            avg = mean(others)
            std = pstdev(others)
            if std == 0:
                if value > avg:
                    peaks.append(label)
                continue
            if value > avg + z * std:
                peaks.append(label)
        return peaks

    def build_summary(
        self,
        *,
        metric_name: str,
        direction: str,
        strength: str,
        rolling_change_pp: float,
        consecutive_up: int,
        volatility_level: str,
    ) -> str:
        metric = metric_name.upper()
        direction_cn = {"upward": "上升", "downward": "下降", "stable": "平稳"}[direction]
        strength_cn = {"weak": "弱", "moderate": "中等", "strong": "强"}[strength]
        vol_cn = {"low": "低", "medium": "中", "high": "高"}[volatility_level]

        parts = [f"{metric} 在近期呈现{strength_cn}{direction_cn}趋势"]
        if consecutive_up >= 2:
            parts.append(f"连续 {consecutive_up} 期环比上涨")
        if volatility_level in ("medium", "high"):
            parts.append(f"波动性{vol_cn}")
        change_sign = "+" if rolling_change_pp >= 0 else ""
        parts.append(
            f"最新滚动均值较基线变动 {change_sign}{rolling_change_pp}pp"
        )
        return "，".join(parts) + "。"

    @staticmethod
    def rolling_window_for_days(window_days: int, aggregation_level: str) -> int:
        if aggregation_level == "day":
            return max(1, window_days)
        if aggregation_level == "week":
            return max(1, math.ceil(window_days / 7))
        raise ValueError(f"不支持的 aggregation_level: {aggregation_level}")
