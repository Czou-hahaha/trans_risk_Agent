"""trend_analysis_skill — 时序风险分析编排。"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from models.exceptions import MetricDataNotFoundError
from models.trend import TrendAnalysisResult, TrendFinding
from tools.engines.trend_engine import TrendEngine
from tools.repositories.trend_repository import TrendRepository
from workflow.constants import REFERENCE_DATE

logger = logging.getLogger(__name__)


class TrendAnalysisSkill:
    """分析指标在滚动窗口内的趋势，可独立运行（尚未接入 workflow）。"""

    def __init__(
        self,
        monitor_session: Session,
        contribution_session: Session | None = None,
    ) -> None:
        self._repo = TrendRepository(monitor_session, contribution_session)
        self._engine = TrendEngine()

    def run(
        self,
        metric_name: str,
        window_days: int = 60,
        aggregation_level: str = "week",
        *,
        end_date: date | None = None,
        channel: str | None = None,
        score_band: str | None = None,
        product: str | None = None,
        region: str | None = None,
    ) -> TrendAnalysisResult:
        end = end_date or REFERENCE_DATE
        start = TrendRepository.window_start(end, window_days)

        points = self._repo.fetch_aggregated_series(
            metric_name=metric_name,
            start_date=start,
            end_date=end,
            aggregation_level=aggregation_level,
            channel=channel,
            score_band=score_band,
            product=product,
            region=region,
        )
        if len(points) < 2:
            logger.error(
                "趋势数据不足 metric=%s window=%sd agg=%s",
                metric_name,
                window_days,
                aggregation_level,
            )
            raise MetricDataNotFoundError(
                f"指标 '{metric_name}' 在 {window_days} 天内数据不足"
                f"（聚合粒度 {aggregation_level}）"
            )

        labels = [p.period_label for p in points]
        values = [p.metric_value for p in points]

        short_roll = TrendEngine.rolling_window_for_days(7, aggregation_level)
        baseline_roll = TrendEngine.rolling_window_for_days(30, aggregation_level)

        output = self._engine.analyze(
            metric_name=metric_name,
            period_labels=labels,
            values=values,
            rolling_window_periods=short_roll,
            baseline_window_periods=baseline_roll,
        )

        generated_at = datetime.now(timezone.utc)
        evidence = {
            "analysis_window_days": window_days,
            "aggregation_level": aggregation_level,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "period_labels": labels,
            "values": [round(v, 6) for v in values],
            "rolling_7d_periods": short_roll,
            "rolling_14d_periods": TrendEngine.rolling_window_for_days(14, aggregation_level),
            "rolling_30d_periods": baseline_roll,
            "sample_sizes": [p.sample_size for p in points],
        }

        finding = TrendFinding(
            finding_type="trend_analysis",
            metric_name=metric_name,
            summary=output.summary,
            evidence=evidence,
            generated_at=generated_at,
            trend_direction=output.trend_direction,
            trend_strength=output.trend_strength,
            rolling_change_pp=output.rolling_change_pp,
            slope_value=output.slope_value,
            volatility_score=output.volatility_score,
            volatility_level=output.volatility_level,
            consecutive_up_periods=output.consecutive_up_periods,
            anomaly_periods=output.anomaly_periods,
            current_value=output.current_value,
            baseline_value=output.baseline_value,
        )

        return TrendAnalysisResult(
            metric_name=metric_name,
            analysis_window_days=window_days,
            aggregation_level=aggregation_level,
            trend_finding=finding,
            generated_at=generated_at,
        )
