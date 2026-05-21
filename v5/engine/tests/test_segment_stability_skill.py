"""SegmentStabilitySkill 测试（mock repository）。"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from skill_runtime.segment_stability import SegmentStabilitySkill
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


class TestSegmentStabilitySkill:
    @patch("skill_runtime.segment_stability.SegmentStabilityRepository")
    def test_run_returns_top_unstable(self, repo_cls: MagicMock) -> None:
        repo = repo_cls.return_value
        repo.fetch_all_segment_series.return_value = {
            "partner_stable": _weekly_points(
                [0.05, 0.0501, 0.0499, 0.05, 0.0502, 0.0498, 0.05, 0.05]
            ),
            "partner_X": _weekly_points(
                [0.03, 0.03, 0.031, 0.029, 0.03, 0.08, 0.09, 0.10]
            ),
        }
        result = SegmentStabilitySkill(MagicMock()).run(
            metric_name="fpd7",
            dimension_name="channel",
            window_days=60,
            top_n=5,
        )
        assert result.metric_name == "fpd7"
        assert result.dimension_name == "channel"
        assert len(result.top_unstable_segments) >= 1
        top = result.top_unstable_segments[0]
        assert top.finding_type == "segment_stability"
        assert top.dimension_value == "partner_X"
        assert top.segment_health in ("unstable", "deteriorating", "watchlist")

    @patch("skill_runtime.segment_stability.SegmentStabilityRepository")
    def test_run_regime_shift_segment_ranked_first(self, repo_cls: MagicMock) -> None:
        repo = repo_cls.return_value
        repo.fetch_all_segment_series.return_value = {
            "stable_a": _weekly_points([0.04] * 8),
            "shift_b": _weekly_points(
                [0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.07, 0.08]
            ),
        }
        result = SegmentStabilitySkill(MagicMock()).run(
            metric_name="fpd7",
            dimension_name="channel",
            window_days=60,
        )
        values = [f.dimension_value for f in result.top_unstable_segments]
        assert values[0] == "shift_b"

    @patch("skill_runtime.segment_stability.SegmentStabilityRepository")
    def test_no_data_raises(self, repo_cls: MagicMock) -> None:
        from models.exceptions import BreakdownDataNotFoundError

        repo_cls.return_value.fetch_all_segment_series.return_value = {}
        with pytest.raises(BreakdownDataNotFoundError):
            SegmentStabilitySkill(MagicMock()).run(
                metric_name="fpd7",
                dimension_name="channel",
                window_days=60,
            )
