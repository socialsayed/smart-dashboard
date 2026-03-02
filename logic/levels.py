def calc_levels(price):
    return {
        "support": round(price * 0.994, 2),
        "resistance": round(price * 1.006, 2),
        "orb_high": round(price * 1.004, 2),
        "orb_low": round(price * 0.996, 2),
    }
