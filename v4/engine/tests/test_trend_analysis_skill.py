"""TrendAnalysisSkill 测试（mock repository）。"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from skill_runtime.trend_analysis import TrendAnalysisSkill
from tools.repositories.trend_repository import TimeSeriesPoint


def _weekly_points(values: list[float], start_week: int = 10) -> list[TimeSeriesPoint]:
    points: list[TimeSeriesPoint] = []
    for i, value in enumerate(values):
        week = start_week + i
        points.append(
            TimeSeriesPoint(
                event_date=date(2026, 1, 5) + timedelta(days=7 * i),
                metric_value=value,
                sample_size=1000 + i * 10,
                period_label=f"2026-W{week:02d}",
            )
        )
    return points


class TestTrendAnalysisSkill:
    @patch("skill_runtime.trend_analysis.TrendRepository")
    def test_run_upward(self, repo_cls: MagicMock) -> None:
        repo = repo_cls.return_value
        repo.fetch_aggregated_series.return_value = _weekly_points(
            [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055]
        )
        skill = TrendAnalysisSkill(MagicMock())
        finding = skill.run(metric_name="fpd7", window_days=60, aggregation_level="week").trend_finding
        assert finding.trend_direction == "upward"
        assert finding.finding_type == "trend_analysis"
        assert "上升" in finding.summary

    @patch("skill_runtime.trend_analysis.TrendRepository")
    def test_run_downward(self, repo_cls: MagicMock) -> None:
        repo = repo_cls.return_value
        repo.fetch_aggregated_series.return_value = _weekly_points(
            [0.08, 0.075, 0.07, 0.065, 0.06, 0.055, 0.05, 0.045]
        )
        finding = TrendAnalysisSkill(MagicMock()).run(metric_name="fpd7", window_days=60).trend_finding
        assert finding.trend_direction == "downward"

    @patch("skill_runtime.trend_analysis.TrendRepository")
    def test_insufficient_data(self, repo_cls: MagicMock) -> None:
        from models.exceptions import MetricDataNotFoundError

        repo_cls.return_value.fetch_aggregated_series.return_value = _weekly_points([0.05])
        with pytest.raises(MetricDataNotFoundError):
            TrendAnalysisSkill(MagicMock()).run(metric_name="fpd7", window_days=60)
