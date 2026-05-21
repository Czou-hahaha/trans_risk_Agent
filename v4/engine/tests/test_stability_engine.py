"""StabilityEngine 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from tools.engines.stability_engine import StabilityEngine


def _labels(n: int, prefix: str = "2026-W") -> list[str]:
    return [f"{prefix}{10 + i:02d}" for i in range(n)]


class TestStabilityEngine:
    def setup_method(self) -> None:
        self.engine = StabilityEngine()

    def test_stable_segment(self) -> None:
        values = [0.05, 0.0501, 0.0499, 0.05, 0.0502, 0.0498, 0.05, 0.05]
        labels = _labels(len(values))
        out = self.engine.analyze(
            metric_name="fpd7",
            dimension_name="channel",
            dimension_value="partner_stable",
            period_labels=labels,
            values=values,
        )
        assert out.volatility_level == "low"
        assert out.stability_score >= 0.7
        assert out.segment_health == "healthy"
        assert out.regime_shift_detected is False

    def test_high_volatility(self) -> None:
        values = [0.02, 0.08, 0.03, 0.09, 0.025, 0.085, 0.02, 0.09]
        vol = self.engine.calculate_volatility(values)
        assert vol.volatility_level == "high"
        out = self.engine.analyze(
            metric_name="fpd7",
            dimension_name="channel",
            dimension_value="partner_volatile",
            period_labels=_labels(len(values)),
            values=values,
        )
        assert out.volatility_level == "high"
        assert out.stability_score < 0.5

    def test_regime_shift(self) -> None:
        values = [0.03, 0.03, 0.031, 0.029, 0.03, 0.03, 0.06, 0.065]
        regime = self.engine.detect_regime_shift(values, recent_periods=2)
        assert regime.regime_shift_detected is True
        assert regime.recent_mean > regime.historical_mean
        out = self.engine.analyze(
            metric_name="fpd7",
            dimension_name="channel",
            dimension_value="partner_X",
            period_labels=_labels(len(values)),
            values=values,
            recent_window_periods=2,
        )
        assert out.regime_shift_detected is True

    def test_consecutive_deterioration(self) -> None:
        values = [0.03, 0.032, 0.034, 0.036, 0.038, 0.04, 0.042, 0.044]
        assert self.engine.analyze_consecutive_deterioration(values) == 7
        out = self.engine.analyze(
            metric_name="fpd7",
            dimension_name="channel",
            dimension_value="partner_up",
            period_labels=_labels(len(values)),
            values=values,
        )
        assert out.consecutive_up_periods >= 4
        assert out.segment_health == "deteriorating"
        assert out.trend_direction == "upward"

    def test_unstable_segment(self) -> None:
        values = [0.03, 0.03, 0.031, 0.029, 0.03, 0.08, 0.09, 0.10]
        out = self.engine.analyze(
            metric_name="fpd7",
            dimension_name="channel",
            dimension_value="partner_X",
            period_labels=_labels(len(values)),
            values=values,
            recent_window_periods=2,
        )
        assert out.volatility_level == "high"
        assert out.regime_shift_detected is True
        assert out.segment_health == "unstable"

    def test_calculate_stability_score_bounds(self) -> None:
        assert self.engine.calculate_stability_score(0.0) == 1.0
        assert 0.0 <= self.engine.calculate_stability_score(0.5) <= 1.0

    def test_requires_minimum_points(self) -> None:
        with pytest.raises(ValueError, match="至少"):
            self.engine.analyze(
                metric_name="fpd7",
                dimension_name="channel",
                dimension_value="x",
                period_labels=["2026-W10"],
                values=[0.05],
            )
