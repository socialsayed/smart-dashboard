# =====================================================
# TRADE DECISION LOGIC
# =====================================================

def trade_decision(
    open_now,
    risk_status,
    index_pcr,
    price,
    resistance,
    options_bias="NEUTRAL"
):
    # Market status
    if not open_now:
        return False, "Market closed"

    # Risk limits
    if not risk_status[0]:
        return False, risk_status[1]

    # Index PCR filter
    if index_pcr < 0.9:
        return False, "Index PCR bearish"

    # Options-aware filter
    if options_bias == "BEARISH":
        return False, "Options bias bearish"

    # Location filter
    if price and resistance and price >= resistance * 0.998:
        return False, "Near resistance"

    return True, "Trade allowed"
