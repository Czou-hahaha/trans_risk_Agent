"""segment_stability_skill — 客群/渠道风险结构稳定性编排。"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from models.exceptions import BreakdownDataNotFoundError
from models.segment_stability import SegmentStabilityFinding, SegmentStabilityResult
from tools.engines.stability_engine import StabilityEngine, StabilityEngineOutput
from tools.repositories.segment_stability_repository import SegmentStabilityRepository
from workflow.constants import REFERENCE_DATE

logger = logging.getLogger(__name__)


class SegmentStabilitySkill:
    """分析各 segment 时序稳定性，可独立运行（尚未接入 workflow）。"""

    def __init__(self, contribution_session: Session) -> None:
        self._repo = SegmentStabilityRepository(contribution_session)
        self._engine = StabilityEngine()

    def run(
        self,
        metric_name: str,
        dimension_name: str,
        window_days: int = 60,
        top_n: int = 10,
        *,
        end_date: date | None = None,
        aggregation_level: str = "week",
        recent_days: int = 14,
    ) -> SegmentStabilityResult:
        end = end_date or REFERENCE_DATE
        start = SegmentStabilityRepository.window_start(end, window_days)

        all_series = self._repo.fetch_all_segment_series(
            metric_name=metric_name,
            dimension_name=dimension_name,
            start_date=start,
            end_date=end,
            aggregation_level=aggregation_level,
        )
        if not all_series:
            logger.error(
                "segment 稳定性数据不足 metric=%s dimension=%s window=%sd",
                metric_name,
                dimension_name,
                window_days,
            )
            raise BreakdownDataNotFoundError(
                f"指标 '{metric_name}' 维度 '{dimension_name}' "
                f"在 {window_days} 天内无足够 segment 序列"
            )

        roll_window = StabilityEngine.rolling_window_for_days(7, aggregation_level)
        recent_window = StabilityEngine.recent_window_for_days(
            recent_days, aggregation_level
        )

        findings: list[SegmentStabilityFinding] = []
        generated_at = datetime.now(timezone.utc)

        for dimension_value, points in all_series.items():
            labels = [p.period_label for p in points]
            values = [p.metric_value for p in points]
            try:
                output = self._engine.analyze(
                    metric_name=metric_name,
                    dimension_name=dimension_name,
                    dimension_value=dimension_value,
                    period_labels=labels,
                    values=values,
                    rolling_window_periods=roll_window,
                    recent_window_periods=recent_window,
                )
            except ValueError as exc:
                logger.warning(
                    "跳过 segment %s=%s: %s",
                    dimension_name,
                    dimension_value,
                    exc,
                )
                continue

            findings.append(
                self._to_finding(
                    metric_name=metric_name,
                    dimension_name=dimension_name,
                    dimension_value=dimension_value,
                    output=output,
                    labels=labels,
                    values=values,
                    window_days=window_days,
                    start=start,
                    end=end,
                    generated_at=generated_at,
                )
            )

        if not findings:
            raise BreakdownDataNotFoundError(
                f"指标 '{metric_name}' 维度 '{dimension_name}' 无有效稳定性分析结果"
            )

        ranked = self._rank_by_instability(findings)[:top_n]

        return SegmentStabilityResult(
            metric_name=metric_name,
            dimension_name=dimension_name,
            analysis_window_days=window_days,
            top_unstable_segments=ranked,
            generated_at=generated_at,
        )

    @staticmethod
    def _rank_by_instability(
        findings: list[SegmentStabilityFinding],
    ) -> list[SegmentStabilityFinding]:
        health_priority = {
            "unstable": 0,
            "deteriorating": 1,
            "watchlist": 2,
            "healthy": 3,
        }

        def sort_key(f: SegmentStabilityFinding) -> tuple:
            return (
                health_priority.get(f.segment_health, 2),
                f.stability_score,
                -f.volatility_score,
                -f.consecutive_up_periods,
            )

        return sorted(findings, key=sort_key)

    @staticmethod
    def _to_finding(
        *,
        metric_name: str,
        dimension_name: str,
        dimension_value: str,
        output: StabilityEngineOutput,
        labels: list[str],
        values: list[float],
        window_days: int,
        start: date,
        end: date,
        generated_at: datetime,
    ) -> SegmentStabilityFinding:
        evidence = {
            "analysis_window_days": window_days,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "period_labels": labels,
            "values": [round(v, 6) for v in values],
        }
        return SegmentStabilityFinding(
            finding_type="segment_stability",
            metric_name=metric_name,
            summary=output.summary,
            evidence=evidence,
            generated_at=generated_at,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            stability_score=output.stability_score,
            volatility_score=output.volatility_score,
            volatility_level=output.volatility_level,
            trend_direction=output.trend_direction,
            consecutive_up_periods=output.consecutive_up_periods,
            regime_shift_detected=output.regime_shift_detected,
            segment_health=output.segment_health,
            current_metric_value=output.current_metric_value,
            baseline_metric_value=output.baseline_metric_value,
        )
