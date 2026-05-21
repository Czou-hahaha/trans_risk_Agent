"""Registry of all supported deterministic pattern detectors."""

from __future__ import annotations

from intelligence_memory.patterns.pattern_detector import (
    ApprovalRiskShiftDetector,
    PatternDetector,
    RecurringContributorDetector,
    RecurringSegmentInstabilityDetector,
    StrategySideEffectDetector,
    VolumeRiskTradeoffDetector,
)

_DEFAULT_DETECTORS: list[PatternDetector] = [
    RecurringContributorDetector(),
    RecurringSegmentInstabilityDetector(),
    StrategySideEffectDetector(),
    ApprovalRiskShiftDetector(),
    VolumeRiskTradeoffDetector(),
]


class PatternRegistry:
    """Unified registry for pattern detector implementations."""

    def __init__(self, detectors: list[PatternDetector] | None = None) -> None:
        self._detectors = list(detectors) if detectors is not None else list(_DEFAULT_DETECTORS)
        self._by_type: dict[str, PatternDetector] = {}
        for detector in self._detectors:
            self._by_type[detector.pattern_type] = detector

    @property
    def supported_pattern_types(self) -> list[str]:
        return [d.pattern_type for d in self._detectors]

    def get(self, pattern_type: str) -> PatternDetector | None:
        return self._by_type.get(pattern_type)

    def all_detectors(self) -> list[PatternDetector]:
        return list(self._detectors)

    def register(self, detector: PatternDetector) -> None:
        self._detectors.append(detector)
        self._by_type[detector.pattern_type] = detector
