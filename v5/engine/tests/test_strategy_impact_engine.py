"""StrategyImpactEngine 单元测试。"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from tools.engines.strategy_impact_engine import (
    DailyMetricObservation,
    StrategyImpactEngine,
)


DEPLOY = date(2026, 5, 10)


def _daily_series(
    *,
    metric_name: str,
    deploy: date,
    before_days: int,
    after_days: int,
    before_value: float,
    after_value: float,
    sample_size: int = 1000,
) -> list[DailyMetricObservation]:
    obs: list[DailyMetricObservation] = []
    for i in range(before_days):
        d = deploy - timedelta(days=before_days - i)
        obs.append(
            DailyMetricObservation(
                event_date=d,
                metric_name=metric_name,
                metric_value=before_value,
                sample_size=sample_size,
            )
        )
    for i in range(after_days):
        d = deploy + timedelta(days=i)
        obs.append(
            DailyMetricObservation(
                event_date=d,
                metric_name=metric_name,
                metric_value=after_value,
                sample_size=sample_size,
            )
        )
    return obs


def _build_observations(
    *,
    approval_before: float,
    approval_after: float,
    fpd7_before: float,
    fpd7_after: float,
    volume_before: float,
    volume_after: float,
    before_days: int = 14,
    after_days: int = 14,
) -> list[DailyMetricObservation]:
    obs: list[DailyMetricObservation] = []
    obs.extend(
        _daily_series(
            metric_name="approval_rate",
            deploy=DEPLOY,
            before_days=before_days,
            after_days=after_days,
            before_value=approval_before,
            after_value=approval_after,
        )
    )
    obs.extend(
        _daily_series(
            metric_name="fpd7",
            deploy=DEPLOY,
            before_days=before_days,
            after_days=after_days,
            before_value=fpd7_before,
            after_value=fpd7_after,
        )
    )
    obs.extend(
        _daily_series(
            metric_name="volume",
            deploy=DEPLOY,
            before_days=before_days,
            after_days=after_days,
            before_value=volume_before,
            after_value=volume_after,
        )
    )
    return obs


class TestStrategyImpactEngine:
    def setup_method(self) -> None:
        self.engine = StrategyImpactEngine()

    def test_highly_effective_strategy(self) -> None:
        obs = _build_observations(
            approval_before=0.72,
            approval_after=0.712,
            fpd7_before=0.050,
            fpd7_after=0.038,
            volume_before=10000,
            volume_after=9800,
        )
        out = self.engine.analyze(
            strategy_name="RISK_HE",
            deployment_date=DEPLOY,
            observations=obs,
        )
        assert out.strategy_effectiveness == "highly_effective"
        assert out.fpd7_delta_pp < -0.5
        assert out.approval_delta_pp > -2.0

    def test_effective_strategy(self) -> None:
        obs = _build_observations(
            approval_before=0.65,
            approval_after=0.618,
            fpd7_before=0.050,
            fpd7_after=0.039,
            volume_before=10000,
            volume_after=9150,
        )
        out = self.engine.analyze(
            strategy_name="RISK_003",
            deployment_date=DEPLOY,
            observations=obs,
        )
        assert out.strategy_effectiveness == "effective"
        assert out.fpd7_delta_pp == pytest.approx(-1.1, abs=0.15)
        assert out.approval_delta_pp == pytest.approx(-3.2, abs=0.15)
        assert out.volume_delta_pct == pytest.approx(-8.5, abs=0.5)

    def test_over_tightened_strategy(self) -> None:
        obs = _build_observations(
            approval_before=0.70,
            approval_after=0.65,
            fpd7_before=0.050,
            fpd7_after=0.047,
            volume_before=10000,
            volume_after=9000,
        )
        out = self.engine.analyze(
            strategy_name="RISK_OT",
            deployment_date=DEPLOY,
            observations=obs,
        )
        assert out.strategy_effectiveness == "over_tightened"
        assert out.approval_delta_pp <= -4.0
        assert out.fpd7_delta_pp > -0.5

    def test_ineffective_strategy(self) -> None:
        obs = _build_observations(
            approval_before=0.70,
            approval_after=0.667,
            fpd7_before=0.050,
            fpd7_after=0.052,
            volume_before=10000,
            volume_after=9500,
        )
        out = self.engine.analyze(
            strategy_name="RISK_BAD",
            deployment_date=DEPLOY,
            observations=obs,
        )
        assert out.strategy_effectiveness == "ineffective"
        assert out.fpd7_delta_pp >= 0

    def test_neutral_strategy(self) -> None:
        obs = _build_observations(
            approval_before=0.70,
            approval_after=0.7005,
            fpd7_before=0.050,
            fpd7_after=0.0501,
            volume_before=10000,
            volume_after=10020,
        )
        out = self.engine.analyze(
            strategy_name="RISK_FLAT",
            deployment_date=DEPLOY,
            observations=obs,
        )
        assert out.strategy_effectiveness == "neutral"

    def test_aggregate_before_after_metrics(self) -> None:
        obs = _build_observations(
            approval_before=0.60,
            approval_after=0.50,
            fpd7_before=0.04,
            fpd7_after=0.03,
            volume_before=500,
            volume_after=400,
        )
        agg = self.engine.aggregate_before_after_metrics(
            observations=obs,
            deployment_date=DEPLOY,
            before_window_days=14,
            after_window_days=14,
            metric_names=["approval_rate", "fpd7", "volume"],
        )
        assert agg.before["approval_rate"] == pytest.approx(0.60)
        assert agg.after["approval_rate"] == pytest.approx(0.50)

    def test_calculate_metric_delta_rate_and_volume(self) -> None:
        rate = self.engine.calculate_metric_delta("fpd7", 0.05, 0.04)
        assert rate.delta_pp == pytest.approx(-1.0)
        vol = self.engine.calculate_metric_delta("volume", 1000, 900)
        assert vol.delta_pct == pytest.approx(-10.0)

    def test_calculate_tradeoff_efficiency(self) -> None:
        eff = self.engine.calculate_tradeoff_efficiency(
            fpd7_delta_pp=-1.1,
            approval_delta_pp=-3.2,
            volume_delta_pct=-8.5,
        )
        assert eff == pytest.approx(1.1 / 3.2, rel=0.01)

    def test_generate_deterministic_summary_no_llm(self) -> None:
        summary = self.engine.generate_deterministic_summary(
            strategy_name="RISK_003",
            deployment_date=DEPLOY,
            before_window_days=14,
            after_window_days=14,
            fpd7_delta_pp=-1.1,
            approval_delta_pp=-3.2,
            volume_delta_pct=-8.5,
            risk_reduction_efficiency=0.34,
            strategy_effectiveness="effective",
        )
        assert "RISK_003" in summary
        assert "有效" in summary

    def test_insufficient_data_raises(self) -> None:
        obs = _daily_series(
            metric_name="approval_rate",
            deploy=DEPLOY,
            before_days=14,
            after_days=14,
            before_value=0.7,
            after_value=0.6,
        )
        with pytest.raises(ValueError, match="数据不足"):
            self.engine.analyze(
                strategy_name="RISK_X",
                deployment_date=DEPLOY,
                observations=obs,
            )
