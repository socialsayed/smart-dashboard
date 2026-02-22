import numpy as np
from datetime import datetime

def build_feature_vector(context: dict) -> dict:
    """
    Takes live dashboard context and returns ML-ready features
    """

    features = {}

    # ----------------------------
    # PRICE & STRUCTURE
    # ----------------------------
    price = context["price"]
    vwap = context["vwap"]

    features["price_vs_vwap"] = (price - vwap) / vwap if vwap else 0.0
    features["vwap_slope"] = context.get("vwap_slope", 0.0)

    features["distance_from_support"] = (
        (price - context["support"]) / price
        if context.get("support") else 0.0
    )

    features["distance_from_resistance"] = (
        (context["resistance"] - price) / price
        if context.get("resistance") else 0.0
    )

    features["orb_range_pct"] = context.get("orb_range", 0.0)
    features["above_orb_high"] = int(context.get("above_orb_high", False))
    features["below_orb_low"] = int(context.get("below_orb_low", False))

    # ----------------------------
    # TREND & MOMENTUM
    # ----------------------------
    features["higher_highs_count"] = context.get("higher_highs", 0)
    features["higher_lows_count"] = context.get("higher_lows", 0)
    features["trend_strength"] = context.get("trend_strength", 0)
    features["range_expansion"] = context.get("range_expansion", 0.0)

    # ----------------------------
    # OPTIONS & SENTIMENT
    # ----------------------------
    features["index_pcr"] = context.get("index_pcr", 1.0)
    features["options_bias"] = context.get("options_bias", 0)
    features["atm_pcr"] = context.get("atm_pcr", 1.0)
    features["ce_oi_delta"] = context.get("ce_oi_delta", 0.0)
    features["pe_oi_delta"] = context.get("pe_oi_delta", 0.0)

    # ----------------------------
    # TIME FEATURES
    # ----------------------------
    minutes = context.get("minutes_since_open", 0)
    features["minutes_since_open"] = minutes

    features["time_bucket"] = min(minutes // 60, 5)
    features["is_first_hour"] = int(minutes <= 60)
    features["is_lunch_time"] = int(120 <= minutes <= 210)
    features["is_last_hour"] = int(minutes >= 330)

    # ----------------------------
    # RISK & BEHAVIOR
    # ----------------------------
    features["trades_today"] = context.get("trades_today", 0)
    features["current_pnl"] = context.get("current_pnl", 0.0)
    features["loss_streak"] = context.get("loss_streak", 0)
    features["recent_trade_gap_min"] = context.get("recent_trade_gap_min", 999)

    return features