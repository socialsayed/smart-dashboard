"""
Rule-based trade confidence engine.

PURPOSE:
- Compute GRADUAL trade quality score (0–100)
- Generate explainable confidence reasons
- NEVER block trades
- NEVER reference ML
- SINGLE source of confidence truth

This file is called ONLY after:
- evaluate_trade_setup() returns allowed=True
"""

from typing import Dict, List, Tuple


# =====================================================
# CONFIDENCE LABELS
# =====================================================
def confidence_label(score: int) -> str:
    if score >= 75:
        return "HIGH"
    elif score >= 60:
        return "MODERATE"
    elif score >= 45:
        return "LOW"
    return "NO_TRADE"


# =====================================================
# CORE CONFIDENCE ENGINE
# =====================================================
def calculate_trade_confidence(
    *,
    snapshot: Dict,
    price: float,
    direction: str = "BUY",
    index_pcr: float | None = None,
    options_bias: str = "NEUTRAL",
    risk_context: Dict | None = None,
    time_context: Dict | None = None,
) -> Tuple[int, List[str]]:
    """
    Returns:
        confidence_score (0–100),
        confidence_reasons (list[str])

    HARD RULE:
    - This function NEVER blocks trades
    - It ONLY scores quality
    """

    score = 0
    reasons: List[str] = []

    vwap = snapshot.get("vwap")
    rsi = snapshot.get("rsi")
    ema_20 = snapshot.get("ema_20")
    ema_50 = snapshot.get("ema_50")

    # -------------------------------------------------
    # 1️⃣ VWAP ALIGNMENT (MAX 25)
    # -------------------------------------------------
    if vwap:
        distance = abs(price - vwap) / vwap

        if direction == "BUY" and price > vwap:
            score += 15
            reasons.append("Price above VWAP (bullish bias)")
        elif direction == "SELL" and price < vwap:
            score += 15
            reasons.append("Price below VWAP (bearish bias)")
        else:
            score += 5
            reasons.append("Price on weak side of VWAP")

        if distance < 0.003:
            score += 10
            reasons.append("Price close to VWAP (low slippage)")
        elif distance < 0.01:
            score += 5
            reasons.append("Price moderately extended from VWAP")
        else:
            reasons.append("Price far from VWAP (extension risk)")
    else:
        score += 5
        reasons.append("VWAP unavailable (confidence reduced)")

    # -------------------------------------------------
    # 2️⃣ TREND STRUCTURE (MAX 20)
    # -------------------------------------------------
    if ema_20 and ema_50:
        if ema_20 > ema_50:
            score += 20
            reasons.append("Short-term trend above medium-term EMA")
        else:
            score += 5
            reasons.append("Trend weak or against position")
    else:
        score += 8
        reasons.append("EMA trend unavailable")

    # -------------------------------------------------
    # 3️⃣ RSI CONTEXT (MAX 15)
    # -------------------------------------------------
    if rsi:
        if 45 <= rsi <= 65:
            score += 15
            reasons.append("RSI in healthy momentum zone")
        elif rsi > 70:
            score += 5
            reasons.append("RSI overbought (risk of pullback)")
        elif rsi < 30:
            score += 5
            reasons.append("RSI oversold (risk of bounce)")
        else:
            score += 8
            reasons.append("RSI neutral")
    else:
        score += 8
        reasons.append("RSI unavailable")

    # -------------------------------------------------
    # 4️⃣ INDEX PCR CONTEXT (MAX 15)
    # -------------------------------------------------
    if index_pcr is not None:
        if direction == "BUY" and index_pcr > 1.0:
            score += 15
            reasons.append("Index PCR supports long bias")
        elif direction == "SELL" and index_pcr < 1.0:
            score += 15
            reasons.append("Index PCR supports short bias")
        else:
            score += 5
            reasons.append("Index PCR weakly aligned")
    else:
        score += 5
        reasons.append("Index PCR unavailable")

    # -------------------------------------------------
    # 5️⃣ OPTIONS BIAS (MAX 10)
    # -------------------------------------------------
    if options_bias == "BULLISH" and direction == "BUY":
        score += 10
        reasons.append("Options bias bullish")
    elif options_bias == "BEARISH" and direction == "SELL":
        score += 10
        reasons.append("Options bias bearish")
    else:
        score += 3
        reasons.append("Options bias neutral or mixed")

    # -------------------------------------------------
    # 6️⃣ RISK CONTEXT (PENALTY ONLY)
    # -------------------------------------------------
    if risk_context:
        trades = risk_context.get("trades", 0)
        pnl = risk_context.get("pnl", 0)

        if trades >= 5:
            score -= 5
            reasons.append("Multiple trades today (fatigue risk)")

        if pnl < 0:
            score -= 5
            reasons.append("Currently in drawdown")

    # -------------------------------------------------
    # NORMALIZE & CLAMP
    # -------------------------------------------------
    score = max(0, min(int(score), 100))

    return score, reasons