# =====================================================
# FULL MARKET SCANNER (PATCHED)
# =====================================================

import pandas as pd
from services.prices import live_price


def scan_market(symbols, min_price=0, min_volume=0, query=""):
    """
    Returns ranked DataFrame of active stocks
    """

    rows = []

    for sym in symbols:
        price, src = live_price(sym)
        if not price:
            continue

        # Simple activity proxy (price * random weight)
        activity_score = price

        if price < min_price:
            continue

        if query and query.upper() not in sym:
            continue

        rows.append({
            "Symbol": sym,
            "Price": price,
            "Source": src,
            "Activity": activity_score
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("Activity", ascending=False)

    return df.reset_index(drop=True)
