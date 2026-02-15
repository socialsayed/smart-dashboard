def trade_decision(
    market_open,
    risk_status,
    pcr,
    price,
    resistance
):
    if not market_open:
        return False, "Market closed"
    if not risk_status[0]:
        return False, risk_status[1]
    if pcr < 0.9:
        return False, "PCR bearish"
    if price and price >= resistance * 0.998:
        return False, "Near resistance"
    return True, "Trade allowed"
