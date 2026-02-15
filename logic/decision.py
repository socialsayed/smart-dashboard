def trade_decision(
    open_now,
    risk_status,
    index_pcr,
    price,
    resistance,
    options_bias="NEUTRAL"
):
    # 1️⃣ Market check
    if not open_now:
        return False, "Market closed"

    # 2️⃣ Risk check (supports tuple OR bool)
    if isinstance(risk_status, tuple):
        if not risk_status[0]:
            return False, risk_status[1]
    else:
        if not risk_status:
            return False, "Risk blocked"

    # 3️⃣ PCR check
    if index_pcr is not None and index_pcr < 0.9:
        return False, "PCR bearish"

    # 4️⃣ Options bias filter
    if options_bias == "BEARISH":
        return False, "Options bias bearish"

    # 5️⃣ Price location
    if price and resistance and price >= resistance * 0.998:
        return False, "Near resistance"

    return True, "Trade allowed"
