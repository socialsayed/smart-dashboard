# =====================================================
# OPTIONS HELPERS (Fallback / Status Utilities)
# =====================================================

def get_fallback_options_snapshot():
    """
    Delayed / indicative options sentiment
    SAFE for mobile & cloud users
    """
    return {
        "spot": "NIFTY 50",
        "pcr": 1.02,
        "bias": "NEUTRAL",
        "oi_summary": "Balanced PUT & CALL activity",
        "data_type": "Delayed / Indicative",
    }