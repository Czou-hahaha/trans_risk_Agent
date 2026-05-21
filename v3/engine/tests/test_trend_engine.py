"""TrendEngine 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from tools.engines.trend_engine import TrendEngine


def _labels(n: int, prefix: str = "2026-W") -> list[str]:
    return [f"{prefix}{10 + i:02d}" for i in range(n)]


class TestTrendEngine:
    def setup_method(self) -> None:
        self.engine = TrendEngine()

    def test_upward_trend(self) -> None:
        values = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055]
        labels = _labels(len(values))
        out = self.engine.analyze(
            metric_name="fpd7",
            period_labels=labels,
            values=values,
            rolling_window_periods=2,
            baseline_window_periods=3,
        )
        assert out.trend_direction == "upward"
        assert out.consecutive_up_periods >= 1
        assert out.rolling_change_pp > 0
        assert "上升" in out.summary

    def test_downward_trend(self) -> None:
        values = [0.08, 0.075, 0.07, 0.065, 0.06, 0.055, 0.05, 0.045]
        labels = _labels(len(values))
        out = self.engine.analyze(
            metric_name="fpd7",
            period_labels=labels,
            values=values,
            rolling_window_periods=2,
            baseline_window_periods=3,
        )
        assert out.trend_direction == "downward"
        assert out.rolling_change_pp < 0
        assert "下降" in out.summary

    def test_stable_trend(self) -> None:
        values = [0.05, 0.0501, 0.0499, 0.05, 0.0502, 0.0498, 0.05, 0.05]
        labels = _labels(len(values))
        out = self.engine.analyze(
            metric_name="fpd7",
            period_labels=labels,
            values=values,
            rolling_window_periods=2,
            baseline_window_periods=3,
        )
        assert out.trend_direction == "stable"

    def test_high_volatility(self) -> None:
        values = [0.02, 0.08, 0.03, 0.09, 0.025, 0.085, 0.02, 0.09]
        _, level = self.engine.volatility_metrics(values)
        assert level == "high"

    def test_consecutive_deterioration(self) -> None:
        values = [0.03, 0.032, 0.034, 0.036, 0.038, 0.04]
        assert self.engine.count_consecutive_up(values) == 5

    def test_peak_detection(self) -> None:
        values = [0.03, 0.03, 0.03, 0.03, 0.03, 0.20, 0.21]
        labels = _labels(len(values))
        peaks = self.engine.detect_peak_periods(values, labels)
        assert "2026-W15" in peaks
        assert "2026-W16" in peaks

    def test_rolling_average_windows(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        roll7 = self.engine.rolling_average(values, 3)
        assert roll7[-1] == pytest.approx(4.0)

    def test_requires_minimum_points(self) -> None:
        with pytest.raises(ValueError, match="至少"):
            self.engine.analyze(
                metric_name="fpd7",
                period_labels=["2026-W10"],
                values=[0.05],
                rolling_window_periods=1,
                baseline_window_periods=1,
            )
