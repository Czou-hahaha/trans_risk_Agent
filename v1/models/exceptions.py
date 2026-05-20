"""Shared exceptions for skills and tools."""


class MetricMonitorError(Exception):
    """Base error for metric monitor."""


class MetricDataNotFoundError(MetricMonitorError):
    """No metric observations for the requested period."""


class MetricQueryError(MetricMonitorError):
    """Database query failed for metrics."""


class DimensionContributionError(Exception):
    """Base error for dimension contribution."""


class BreakdownDataNotFoundError(DimensionContributionError):
    """No breakdown rows for the requested period/dimension."""


class BreakdownQueryError(DimensionContributionError):
    """Database query failed for breakdowns."""
