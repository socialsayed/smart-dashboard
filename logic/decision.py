# =====================================================
# TRADE DECISION LOGIC
# =====================================================

def trade_decision(
    open_now,
    risk_status,
    index_pcr,
    price,
    resistance,
    options_bias="NEUTRAL",
    confidence_score=None
):
    # Market status
    if not open_now:
        return False, "Market closed"

    # Risk limits
    if not risk_status[0]:
        return False, risk_status[1]

    # Index PCR HARD block (unchanged)
    if index_pcr < 0.9:
        return False, "Index PCR bearish"

    # Options-aware HARD block (unchanged)
    if options_bias == "BEARISH":
        return False, "Options bias bearish"

    # Location filter
    if price and resistance and price >= resistance * 0.998:
        return False, "Near resistance"

    # 🧠 PHASE 1: Confidence gate (SOFT → HARD only at NO_TRADE)
    if confidence_score is not None and confidence_score < 45:
        return False, "Low confidence – insufficient edge"

    return True, "Trade allowed"
    

def score_vwap(price, vwap, vwap_slope):
    if price > vwap and vwap_slope > 0:
        return 30, "Above VWAP with rising slope"
    elif price < vwap and vwap_slope < 0:
        return 30, "Below VWAP with falling slope"
    elif abs(price - vwap) / vwap < 0.001:
        return 15, "Near VWAP – indecision"
    return 5, "Against VWAP bias"


def score_orb(orb_signal):
    if orb_signal == "CONFIRMED":
        return 20, "ORB breakout confirmed"
    elif orb_signal == "WEAK":
        return 10, "ORB breakout weak"
    return 0, "No ORB confirmation"


def score_trend(trend_alignment):
    if trend_alignment == "STRONG":
        return 20, "Strong multi-TF trend alignment"
    elif trend_alignment == "MILD":
        return 10, "Partial trend alignment"
    return 0, "Trend not aligned"


def score_pcr(pcr_value, direction):
    if direction == "BUY" and pcr_value < 0.9:
        return 20, f"Bullish PCR ({pcr_value:.2f})"
    if direction == "SELL" and pcr_value > 1.1:
        return 20, f"Bearish PCR ({pcr_value:.2f})"
    return 5, f"Neutral PCR ({pcr_value:.2f})"

from datetime import datetime
from services.market_time import get_time_quality


def calculate_trade_confidence(context: dict):
    """
    Phase-2 Confidence Engine
    Adds:
    - VWAP slope
    - Trend strength
    """

    score = 0
    reasons = {}

    price = context.get("price")
    vwap = context.get("vwap")
    vwap_slope = context.get("vwap_slope", 0)
    orb_signal = context.get("orb_signal")
    trend_alignment = context.get("trend_alignment")
    pcr = context.get("pcr")
    direction = context.get("direction")

    # ----------------------------------
    # 1️⃣ VWAP POSITION
    # ----------------------------------
    if price and vwap:
        if price > vwap:
            score += 15
            reasons["VWAP Position"] = "Price above VWAP (bullish)"
        else:
            score += 5
            reasons["VWAP Position"] = "Price below VWAP (weak)"

    # ----------------------------------
    # 2️⃣ VWAP SLOPE (NEW – Phase 2)
    # ----------------------------------
    if vwap_slope > 0:
        score += 15
        reasons["VWAP Slope"] = "VWAP rising (trend support)"
    elif vwap_slope < 0:
        score += 5
        reasons["VWAP Slope"] = "VWAP falling (headwind)"
    else:
        score += 8
        reasons["VWAP Slope"] = "VWAP flat (neutral)"

    # ----------------------------------
    # 3️⃣ ORB SIGNAL
    # ----------------------------------
    if orb_signal == "CONFIRMED":
        score += 20
        reasons["ORB"] = "ORB breakout confirmed"
    else:
        score += 8
        reasons["ORB"] = "No ORB confirmation"

    # ----------------------------------
    # 4️⃣ TREND STRENGTH (NEW – Phase 2)
    # ----------------------------------
    if trend_alignment == "STRONG":
        score += 20
        reasons["Trend Strength"] = "Strong trend structure"
    elif trend_alignment == "MILD":
        score += 10
        reasons["Trend Strength"] = "Mild trend"
    else:
        score += 5
        reasons["Trend Strength"] = "Range / weak structure"

    # ----------------------------------
    # 5️⃣ PCR CONFIRMATION
    # ----------------------------------
    if pcr:
        if direction == "BUY" and pcr > 1:
            score += 10
            reasons["PCR"] = "PCR supports long bias"
        elif direction == "SELL" and pcr < 1:
            score += 10
            reasons["PCR"] = "PCR supports short bias"
        else:
            score += 5
            reasons["PCR"] = "PCR neutral / weak"

    # ----------------------------------
    # Normalize score
    # ----------------------------------
    score = min(score, 100)

    return score, reasons

def confidence_label(score):
    if score >= 75:
        return "HIGH"
    elif score >= 60:
        return "MODERATE"
    elif score >= 45:
        return "LOW"
    return "NO_TRADE"
