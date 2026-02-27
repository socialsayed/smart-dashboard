# =====================================================
# SUBSCRIPTION CONFIG — STEP 3A
# =====================================================
# This file defines subscription tiers and capabilities.
#
# IMPORTANT:
# - Config only (NO UI logic here)
# - NO enforcement at this step
# - Used later for soft gating
# - SEBI-safe by design
# =====================================================

# ---- Tier names (single source of truth) ----
TIER_FREE = "FREE"
TIER_BASIC = "BASIC"
TIER_PRO = "PRO"
TIER_ELITE = "ELITE"

# ---- Ordered tiers (lowest → highest) ----
SUBSCRIPTION_TIERS = [
    TIER_FREE,
    TIER_BASIC,
    TIER_PRO,
    TIER_ELITE,
]

# =====================================================
# TIER CAPABILITIES
# =====================================================
# Notes:
# - No trade advice is monetized
# - Limits apply only to visibility / convenience
# - FREE tier remains fully usable
# =====================================================

TIER_CONFIG = {

    TIER_FREE: {
        "label": "Free",
        "description": "Basic market analytics and educational insights",

        # Scanner
        "scanner_max_symbols": 5,
        "scanner_refresh_seconds": 60,

        # Confidence & ML
        "show_confidence_label": True,     # LOW / MEDIUM / HIGH
        "show_confidence_reasons": False,
        "show_ml_score_numeric": False,
        "show_ml_explanations": False,

        # Analytics
        "history_days": 0,                 # summary only
        "show_backtesting": False,

        # Exports
        "allow_csv_export": False,

        # Performance
        "fast_refresh": False,
    },

    TIER_BASIC: {
        "label": "Basic",
        "description": "Enhanced visibility and trade review tools",

        "scanner_max_symbols": 10,
        "scanner_refresh_seconds": 20,

        "show_confidence_label": True,
        "show_confidence_reasons": True,
        "show_ml_score_numeric": False,
        "show_ml_explanations": False,

        "history_days": 14,
        "show_backtesting": False,

        "allow_csv_export": True,

        "fast_refresh": False,
    },

    TIER_PRO: {
        "label": "Pro",
        "description": "Advanced analytics and ML-assisted context",

        "scanner_max_symbols": 20,
        "scanner_refresh_seconds": 10,

        "show_confidence_label": True,
        "show_confidence_reasons": True,
        "show_ml_score_numeric": True,
        "show_ml_explanations": True,

        "history_days": 365,
        "show_backtesting": True,

        "allow_csv_export": True,

        "fast_refresh": True,
    },

    TIER_ELITE: {
        "label": "Elite",
        "description": "Professional-grade analytics and performance",

        "scanner_max_symbols": None,        # unlimited
        "scanner_refresh_seconds": 5,

        "show_confidence_label": True,
        "show_confidence_reasons": True,
        "show_ml_score_numeric": True,
        "show_ml_explanations": True,

        "history_days": None,               # full history
        "show_backtesting": True,

        "allow_csv_export": True,

        "fast_refresh": True,
    },
}

# =====================================================
# DEFAULTS
# =====================================================

# Default tier for all users (until auth/payment exists)
DEFAULT_USER_TIER = TIER_FREE

# Safety guard
def get_tier_config(tier: str):
    """
    Safe accessor for tier config.
    Always returns a valid tier config.
    """
    return TIER_CONFIG.get(tier, TIER_CONFIG[TIER_FREE])