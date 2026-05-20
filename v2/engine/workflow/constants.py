"""Default orchestration parameters for investigation workflow."""

from datetime import date

# PKL observable FPD7 cohort ends ~7d before max apply_date (see seed_from_pkl.py)
DEFAULT_DIMENSIONS: list[str] = [
    "order_tag",
    "risk_level",
    "cus_type",
    "floan_period",
]
DEFAULT_TOP_N = 5
DEFAULT_PERIOD_DAYS = 7
REFERENCE_DATE = date(2026, 3, 7)

# Dimension attribution: single value ≥ this share → not a comparable segment (composition only)
DIMENSION_DOMINANCE_THRESHOLD = 0.98

# User-state / cohort labels — especially prone to misread when sample is single-category
USER_STATUS_DIMENSIONS: frozenset[str] = frozenset(
    {"cus_type", "mob_bin", "cus_type_bin", "age_bin", "age_group"}
)
