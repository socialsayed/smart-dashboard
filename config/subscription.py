# =====================================================
# SUBSCRIPTION CONFIGURATION
# STEP 3E – HISTORICAL DEPTH GATING
# =====================================================

DEFAULT_USER_TIER = "FREE"

TIERS = {
    "FREE": {
        "label": "Free",
        "history_days": 1,          # today only
        "show_ml_explanation": False,
    },
    "BASIC": {
        "label": "Basic",
        "history_days": 7,
        "show_ml_explanation": False,
    },
    "PRO": {
        "label": "Pro",
        "history_days": 7,
        "show_ml_explanation": True,
    },
    "ELITE": {
        "label": "Elite",
        "history_days": None,       # unlimited
        "show_ml_explanation": True,
    },
}


def get_tier_config(tier: str) -> dict:
    """
    Safe tier resolver.
    Always returns a valid config.
    """
    if not tier:
        return TIERS[DEFAULT_USER_TIER]

    tier = tier.upper()
    return TIERS.get(tier, TIERS[DEFAULT_USER_TIER])