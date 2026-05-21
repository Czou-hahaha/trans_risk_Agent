"""Dimension contribution skill — structured attribution analysis only."""

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from models.contribution import (
    AttributionContext,
    ContributionFinding,
    DimensionContributionResult,
)
from models.contribution_input import DimensionContributionInput, PeriodRange
from models.exceptions import BreakdownDataNotFoundError
from tools.engines.contribution_engine import ContributionEngine, ContributorRow
from tools.repositories.breakdown_repository import BreakdownRepository
from workflow.constants import DIMENSION_DOMINANCE_THRESHOLD

logger = logging.getLogger(__name__)


class DimensionContributionSkill:
    """Produce structured dimension attribution results."""

    def __init__(self, session: Session) -> None:
        self._repo = BreakdownRepository(session)
        self._engine = ContributionEngine()

    def run(
        self,
        metric_name: str,
        current_period: PeriodRange | tuple[date, date],
        previous_period: PeriodRange | tuple[date, date],
        dimension_list: list[str],
        top_n: int = 5,
    ) -> DimensionContributionResult:
        cur = self._normalize_period(current_period)
        prev = self._normalize_period(previous_period)

        all_rows: list[ContributorRow] = []
        portfolio_current_rates: list[float] = []
        portfolio_previous_rates: list[float] = []

        for dimension_name in dimension_list:
            rows, cur_port, prev_port = self.analyze_dimension(
                metric_name=metric_name,
                dimension_name=dimension_name,
                current_start=cur.start_date,
                current_end=cur.end_date,
                previous_start=prev.start_date,
                previous_end=prev.end_date,
            )
            all_rows.extend(rows)
            if cur_port is not None:
                portfolio_current_rates.append(cur_port)
            if prev_port is not None:
                portfolio_previous_rates.append(prev_port)

        if not all_rows:
            raise BreakdownDataNotFoundError(
                f"No breakdown data for metric '{metric_name}' "
                f"across dimensions {dimension_list}"
            )

        port_cur = (
            sum(portfolio_current_rates) / len(portfolio_current_rates)
            if portfolio_current_rates
            else None
        )
        port_prev = (
            sum(portfolio_previous_rates) / len(portfolio_previous_rates)
            if portfolio_previous_rates
            else None
        )
        port_delta: float | None = None
        if port_cur is not None and port_prev is not None:
            port_delta = round((port_cur - port_prev) * 100, 2)

        ctx = self._derive_attribution_context(port_delta)
        ranked = self.rank_contributors(all_rows, top_n=top_n, port_delta_pp=port_delta)
        generated_at = datetime.now(timezone.utc)
        findings = self.build_findings(
            metric_name=metric_name,
            rows=ranked,
            current_period=cur,
            previous_period=prev,
            generated_at=generated_at,
        )

        return DimensionContributionResult(
            metric_name=metric_name,
            attribution_context=ctx,
            current_period_start=cur.start_date,
            current_period_end=cur.end_date,
            previous_period_start=prev.start_date,
            previous_period_end=prev.end_date,
            portfolio_current_value=(
                self._engine.rate_to_percent_points(port_cur) if port_cur is not None else None
            ),
            portfolio_previous_value=(
                self._engine.rate_to_percent_points(port_prev) if port_prev is not None else None
            ),
            portfolio_delta_pp=port_delta,
            top_contributors=findings,
            generated_at=generated_at,
        )

    def run_from_input(
        self, input_data: DimensionContributionInput
    ) -> DimensionContributionResult:
        return self.run(
            metric_name=input_data.metric_name,
            current_period=input_data.current_period,
            previous_period=input_data.previous_period,
            dimension_list=input_data.dimension_list,
            top_n=input_data.top_n,
        )

    def analyze_dimension(
        self,
        metric_name: str,
        dimension_name: str,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
    ) -> tuple[list[ContributorRow], float | None, float | None]:
        current_df = self._repo.query_dimension_breakdowns(
            metric_name, dimension_name, current_start, current_end
        )
        previous_df = self._repo.query_dimension_breakdowns(
            metric_name, dimension_name, previous_start, previous_end
        )

        if current_df.empty and previous_df.empty:
            logger.warning(
                "No data for dimension=%s metric=%s", dimension_name, metric_name
            )
            return [], None, None

        current_agg = self._engine.aggregate_period(current_df)
        previous_agg = self._engine.aggregate_period(previous_df)
        threshold = DIMENSION_DOMINANCE_THRESHOLD

        if not self._engine.is_attributable_period(
            current_agg, dominance_threshold=threshold
        ) or not self._engine.is_attributable_period(
            previous_agg, dominance_threshold=threshold
        ):
            logger.info(
                "Skip non-attributable dimension=%s metric=%s "
                "(single-segment dominance ≥%.0f%% in current or previous period)",
                dimension_name,
                metric_name,
                threshold * 100,
            )
            return [], None, None

        rows = self._engine.compare_periods(dimension_name, current_agg, previous_agg)
        rows = self._engine.filter_attributable_contributors(
            rows, dominance_threshold=threshold
        )
        cur_port = self._engine.portfolio_weighted_rate(current_agg)
        prev_port = self._engine.portfolio_weighted_rate(previous_agg)
        return rows, cur_port, prev_port

    def rank_contributors(
        self,
        rows: list[ContributorRow],
        *,
        top_n: int,
        port_delta_pp: float | None = None,
    ) -> list[ContributorRow]:
        ctx = self._derive_attribution_context(port_delta_pp)
        if ctx == AttributionContext.NEUTRAL:
            return self._engine.rank_by_abs_contribution(rows, top_n=top_n)
        descending = ctx == AttributionContext.RISK_DETERIORATION
        return self._engine.rank_by_contribution(
            rows, top_n=top_n, descending=descending
        )

    def build_findings(
        self,
        *,
        metric_name: str,
        rows: list[ContributorRow],
        current_period: PeriodRange,
        previous_period: PeriodRange,
        generated_at: datetime,
    ) -> list[ContributionFinding]:
        findings: list[ContributionFinding] = []
        for rank, row in enumerate(rows, start=1):
            evidence = {
                "dimension_name": row.dimension_name,
                "dimension_value": row.dimension_value,
                "current_period": {
                    "start_date": current_period.start_date.isoformat(),
                    "end_date": current_period.end_date.isoformat(),
                },
                "previous_period": {
                    "start_date": previous_period.start_date.isoformat(),
                    "end_date": previous_period.end_date.isoformat(),
                },
                "current_volume": row.current_volume,
                "previous_volume": row.previous_volume,
                "volume_share": row.volume_share,
            }
            summary = (
                f"{row.dimension_name}={row.dimension_value}: "
                f"contribution_pp={row.contribution_pp:+.4f}, rank={rank}"
            )
            findings.append(
                ContributionFinding(
                    finding_type="dimension_contribution",
                    metric_name=metric_name,
                    summary=summary,
                    evidence=evidence,
                    generated_at=generated_at,
                    dimension_name=row.dimension_name,
                    dimension_value=row.dimension_value,
                    current_value=self._engine.rate_to_percent_points(row.current_rate),
                    previous_value=self._engine.rate_to_percent_points(row.previous_rate),
                    delta_pp=row.delta_pp,
                    contribution_pp=row.contribution_pp,
                    rank=rank,
                )
            )
        return findings

    @staticmethod
    def _derive_attribution_context(portfolio_delta_pp: float | None) -> AttributionContext:
        if portfolio_delta_pp is None or portfolio_delta_pp == 0:
            return AttributionContext.NEUTRAL
        if portfolio_delta_pp > 0:
            return AttributionContext.RISK_DETERIORATION
        return AttributionContext.RISK_IMPROVEMENT

    @staticmethod
    def _normalize_period(
        period: PeriodRange | tuple[date, date],
    ) -> PeriodRange:
        if isinstance(period, PeriodRange):
            return period
        start, end = period
        return PeriodRange(start_date=start, end_date=end)
