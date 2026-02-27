# =====================================================
# SUBSCRIPTION & ACCESS CONFIGURATION
# =====================================================

DEFAULT_USER_TIER = "FREE"

# 🔁 Refresh speed control (seconds)
# Used for STEP 3C – refresh speed gating
LIVE_REFRESH = {
    "FREE": 20,
    "BASIC": 15,
    "PRO": 7,
    "ELITE": 5,
}

TIERS = {
    "FREE": {
        "label": "Free",
        "history_days": 1,
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
        "history_days": None,
        "show_ml_explanation": True,
    },
}


def get_tier_config(tier: str) -> dict:
    if not tier:
        tier = DEFAULT_USER_TIER
    return TIERS.get(tier.upper(), TIERS[DEFAULT_USER_TIER])