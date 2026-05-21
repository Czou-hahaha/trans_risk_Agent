"""strategy_impact_skill — 策略上线前后影响编排。"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models.exceptions import StrategyDataNotFoundError
from models.strategy_impact import StrategyImpactFinding, StrategyImpactResult
from tools.engines.strategy_impact_engine import (
    DEFAULT_METRICS,
    StrategyImpactEngine,
    StrategyImpactEngineOutput,
)
from tools.repositories.strategy_impact_repository import StrategyImpactRepository

logger = logging.getLogger(__name__)


class StrategyImpactSkill:
    """分析策略上线前后指标变化与 tradeoff，可独立运行（尚未接入 workflow）。"""

    def __init__(self, monitor_session: Session) -> None:
        self._repo = StrategyImpactRepository(monitor_session)
        self._engine = StrategyImpactEngine()

    def run(
        self,
        strategy_name: str,
        deployment_date: date,
        before_window_days: int = 14,
        after_window_days: int = 14,
        *,
        metrics: list[str] | None = None,
    ) -> StrategyImpactResult:
        metric_names = list(metrics) if metrics else list(DEFAULT_METRICS)

        observations = self._repo.fetch_strategy_observations(
            strategy_name=strategy_name,
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
            metric_names=metric_names,
        )

        try:
            output = self._engine.analyze(
                strategy_name=strategy_name,
                deployment_date=deployment_date,
                observations=observations,
                before_window_days=before_window_days,
                after_window_days=after_window_days,
                metrics=metric_names,
            )
        except ValueError as exc:
            logger.error(
                "策略影响分析失败 strategy=%s deploy=%s: %s",
                strategy_name,
                deployment_date,
                exc,
            )
            raise StrategyDataNotFoundError(str(exc)) from exc

        generated_at = datetime.now(timezone.utc)
        finding = self._to_finding(
            strategy_name=strategy_name,
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
            output=output,
            metric_names=metric_names,
            generated_at=generated_at,
        )

        return StrategyImpactResult(
            strategy_name=strategy_name,
            deployment_date=deployment_date,
            findings=[finding],
            generated_at=generated_at,
        )

    @staticmethod
    def _to_finding(
        *,
        strategy_name: str,
        deployment_date: date,
        before_window_days: int,
        after_window_days: int,
        output: StrategyImpactEngineOutput,
        metric_names: list[str],
        generated_at: datetime,
    ) -> StrategyImpactFinding:
        start = deployment_date - timedelta(days=before_window_days)
        end = deployment_date + timedelta(days=after_window_days - 1)
        evidence = {
            "before_window_days": before_window_days,
            "after_window_days": after_window_days,
            "analysis_start": start.isoformat(),
            "analysis_end": end.isoformat(),
            "metrics_analyzed": metric_names,
            "metric_deltas": {
                name: {
                    "before": d.before,
                    "after": d.after,
                    "absolute_delta": d.absolute_delta,
                    "delta_pp": d.delta_pp,
                    "delta_pct": d.delta_pct,
                }
                for name, d in output.metric_deltas.items()
            },
        }
        return StrategyImpactFinding(
            finding_type="strategy_impact",
            metric_name="strategy_impact",
            summary=output.summary,
            evidence=evidence,
            generated_at=generated_at,
            strategy_name=strategy_name,
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
            approval_rate_before=output.approval_rate_before,
            approval_rate_after=output.approval_rate_after,
            approval_delta_pp=output.approval_delta_pp,
            fpd7_before=output.fpd7_before,
            fpd7_after=output.fpd7_after,
            fpd7_delta_pp=output.fpd7_delta_pp,
            volume_before=output.volume_before,
            volume_after=output.volume_after,
            volume_delta_pct=output.volume_delta_pct,
            risk_reduction_efficiency=output.risk_reduction_efficiency,
            strategy_effectiveness=output.strategy_effectiveness,
        )
