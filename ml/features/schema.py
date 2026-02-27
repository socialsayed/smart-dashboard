"""
ML Feature Schema (LOCKED)

This file is the SINGLE SOURCE OF TRUTH for:
- Feature names
- Feature order
- Feature version

Changing this file REQUIRES retraining the model.
"""

SCHEMA_VERSION = "1.0.0"

# IMPORTANT:
# - Order matters
# - Do NOT reorder existing features
# - Only append new features at the END
FEATURE_COLUMNS = [
    "price_vs_vwap_pct",
    "vwap_slope",
    "rsi",
    "ema_trend",
    "orb_range_pct",
    "volume_ratio",
    "index_pcr",
    "options_bias_score",
    "time_of_day_minutes",
]


def get_feature_count() -> int:
    return len(FEATURE_COLUMNS)