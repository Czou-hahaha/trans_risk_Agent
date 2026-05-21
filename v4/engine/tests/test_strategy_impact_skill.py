"""StrategyImpactSkill 测试（mock repository）。"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from skill_runtime.strategy_impact import StrategyImpactSkill
from tools.engines.strategy_impact_engine import DailyMetricObservation

DEPLOY = date(2026, 5, 10)


def _observations_effective() -> list[DailyMetricObservation]:
    obs: list[DailyMetricObservation] = []
    for i in range(14):
        d_before = DEPLOY - timedelta(days=14 - i)
        d_after = DEPLOY + timedelta(days=i)
        obs.append(
            DailyMetricObservation(
                d_before, "approval_rate", 0.65, 1000
            )
        )
        obs.append(
            DailyMetricObservation(
                d_after, "approval_rate", 0.618, 1000
            )
        )
        obs.append(DailyMetricObservation(d_before, "fpd7", 0.050, 1000))
        obs.append(DailyMetricObservation(d_after, "fpd7", 0.039, 1000))
        obs.append(DailyMetricObservation(d_before, "volume", 10000.0, 1000))
        obs.append(DailyMetricObservation(d_after, "volume", 9150.0, 1000))
    return obs


class TestStrategyImpactSkill:
    @patch("skill_runtime.strategy_impact.StrategyImpactRepository")
    def test_run_returns_effective_finding(self, repo_cls: MagicMock) -> None:
        repo_cls.return_value.fetch_strategy_observations.return_value = (
            _observations_effective()
        )
        result = StrategyImpactSkill(MagicMock()).run(
            strategy_name="RISK_003",
            deployment_date=DEPLOY,
        )
        assert result.strategy_name == "RISK_003"
        assert result.deployment_date == DEPLOY
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.finding_type == "strategy_impact"
        assert finding.strategy_effectiveness == "effective"
        assert finding.fpd7_delta_pp == pytest.approx(-1.1, abs=0.15)
        assert finding.approval_delta_pp == pytest.approx(-3.2, abs=0.15)

    @patch("skill_runtime.strategy_impact.StrategyImpactRepository")
    def test_run_custom_metrics(self, repo_cls: MagicMock) -> None:
        repo = repo_cls.return_value
        repo.fetch_strategy_observations.return_value = _observations_effective()
        StrategyImpactSkill(MagicMock()).run(
            strategy_name="RISK_003",
            deployment_date=DEPLOY,
            metrics=["approval_rate", "fpd7", "volume"],
        )
        call_kwargs = repo.fetch_strategy_observations.call_args.kwargs
        assert call_kwargs["metric_names"] == [
            "approval_rate",
            "fpd7",
            "volume",
        ]

    @patch("skill_runtime.strategy_impact.StrategyImpactRepository")
    def test_no_data_raises(self, repo_cls: MagicMock) -> None:
        from models.exceptions import StrategyDataNotFoundError

        repo_cls.return_value.fetch_strategy_observations.side_effect = (
            StrategyDataNotFoundError("no data")
        )
        with pytest.raises(StrategyDataNotFoundError):
            StrategyImpactSkill(MagicMock()).run(
                strategy_name="RISK_003",
                deployment_date=DEPLOY,
            )
