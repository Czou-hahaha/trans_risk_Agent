"""Metric monitor skill — period-over-period monitoring and investigation gate."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from models.exceptions import MetricDataNotFoundError
from models.metric_monitor import MetricMonitorFinding
from models.metric_monitor_input import MetricMonitorInput
from models.metric_profiles import get_thresholds, resolve_metric_profile
from skill_runtime import metric_monitor_logic as logic
from tools.repositories.metrics_repository import MetricsRepository

logger = logging.getLogger(__name__)


class MetricMonitorSkill:
    """Orchestrates repository reads and delegates computation to metric_monitor_logic."""

    def __init__(self, session: Session) -> None:
        self._repo = MetricsRepository(session)

    def run(
        self,
        metric_name: str,
        current_start_date: date,
        current_end_date: date,
        previous_start_date: date,
        previous_end_date: date,
        *,
        skip_threshold_pp: float | None = None,
        investigate_threshold_pp: float | None = None,
        risk_up_is_bad: bool | None = None,
        load_prior_period: bool = True,
    ) -> MetricMonitorFinding:
        profile = resolve_metric_profile(metric_name)
        thresholds = get_thresholds(profile)

        if skip_threshold_pp is not None:
            thresholds = thresholds.model_copy(update={"skip_pp": skip_threshold_pp})
        if investigate_threshold_pp is not None:
            thresholds = thresholds.model_copy(
                update={"investigate_pp": investigate_threshold_pp}
            )
        if risk_up_is_bad is not None:
            thresholds = thresholds.model_copy(update={"risk_up_is_bad": risk_up_is_bad})

        current_values = self._load_period_values(
            metric_name, current_start_date, current_end_date, "current"
        )
        previous_values = self._load_period_values(
            metric_name, previous_start_date, previous_end_date, "previous"
        )

        current_avg = logic.period_mean(current_values)
        previous_avg = logic.period_mean(previous_values)
        delta_pp, change_rate = logic.compute_delta(current_avg, previous_avg)

        prior_delta_pp: float | None = None
        if load_prior_period and thresholds.consecutive_enabled:
            prior_start, prior_end = logic.prior_prior_window(
                previous_start_date, previous_end_date
            )
            prior_values = self._try_load_period_values(
                metric_name, prior_start, prior_end
            )
            if prior_values:
                prior_avg = logic.period_mean(prior_values)
                prior_delta_pp, _ = logic.compute_delta(previous_avg, prior_avg)

        direction = logic.compute_direction(delta_pp)
        decision = logic.evaluate_investigation(thresholds, delta_pp, prior_delta_pp)
        severity = logic.compute_severity(
            thresholds,
            abs(delta_pp),
            consecutive_weeks_trend=decision.consecutive_weeks_trend,
            needs_investigation=decision.needs_investigation,
        )
        attribution_hint = logic.resolve_attribution_hint(
            direction,
            risk_up_is_bad=thresholds.risk_up_is_bad,
            consecutive_weeks_trend=decision.consecutive_weeks_trend,
        )

        return logic.build_finding(
            metric_name=metric_name,
            metric_profile=profile,
            thresholds=thresholds,
            current_value=current_avg,
            previous_value=previous_avg,
            delta_pp=delta_pp,
            prior_period_delta_pp=prior_delta_pp,
            change_rate=change_rate,
            direction=direction,
            investigation_gate=decision.gate,
            needs_investigation=decision.needs_investigation,
            severity=severity,
            attribution_hint=attribution_hint,
            consecutive_weeks_trend=decision.consecutive_weeks_trend,
            investigation_triggers=decision.triggers,
            current_start_date=current_start_date,
            current_end_date=current_end_date,
            previous_start_date=previous_start_date,
            previous_end_date=previous_end_date,
        )

    def run_from_input(self, input_data: MetricMonitorInput) -> MetricMonitorFinding:
        return self.run(
            metric_name=input_data.metric_name,
            current_start_date=input_data.current_start_date,
            current_end_date=input_data.current_end_date,
            previous_start_date=input_data.previous_start_date,
            previous_end_date=input_data.previous_end_date,
            skip_threshold_pp=input_data.skip_threshold_pp,
            investigate_threshold_pp=input_data.investigate_threshold_pp,
            risk_up_is_bad=input_data.risk_up_is_bad,
            load_prior_period=input_data.load_prior_period,
        )

    def _load_period_values(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        period_label: str,
    ) -> list[float]:
        df = self._repo.fetch_metric_series(metric_name, start_date, end_date)
        if df.empty:
            logger.error(
                "No metric data metric=%s period=%s range=%s..%s",
                metric_name,
                period_label,
                start_date,
                end_date,
            )
            raise MetricDataNotFoundError(
                f"No data for metric '{metric_name}' ({period_label} period) "
                f"between {start_date} and {end_date}"
            )
        return [float(v) for v in df["metric_value"].tolist()]

    def _try_load_period_values(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
    ) -> list[float] | None:
        df = self._repo.fetch_metric_series(metric_name, start_date, end_date)
        if df.empty:
            logger.info(
                "No prior-prior data metric=%s range=%s..%s (consecutive rule skipped)",
                metric_name,
                start_date,
                end_date,
            )
            return None
        return [float(v) for v in df["metric_value"].tolist()]
