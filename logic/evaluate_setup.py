"""
Trade setup validation logic.
Used by app.py and scanners as a HARD RULE GATE.

DESIGN RULES (LOCKED):
- Indicators are OPTIONAL
- Validation must NEVER crash
- This file DOES NOT compute confidence
- ML is NOT referenced here
- Output contract is STABLE
"""

from typing import Dict, List


# =====================================================
# 🔍 SAFE INDICATOR SNAPSHOT
# =====================================================
def _build_indicator_snapshot(df, price) -> Dict:
    """
    Safely build latest indicator snapshot.
    Missing indicators must degrade gracefully, never crash.
    """

    snapshot = {
        "price": price,
        "vwap": None,
        "rsi": None,
        "ema_20": None,
        "ema_50": None,
    }

    if df is None or df.empty:
        return snapshot

    if "VWAP" in df.columns and not df["VWAP"].dropna().empty:
        snapshot["vwap"] = df["VWAP"].dropna().iloc[-1]

    if "RSI" in df.columns and not df["RSI"].dropna().empty:
        snapshot["rsi"] = df["RSI"].dropna().iloc[-1]

    if "EMA_20" in df.columns and not df["EMA_20"].dropna().empty:
        snapshot["ema_20"] = df["EMA_20"].dropna().iloc[-1]

    if "EMA_50" in df.columns and not df["EMA_50"].dropna().empty:
        snapshot["ema_50"] = df["EMA_50"].dropna().iloc[-1]

    return snapshot


# =====================================================
# 🧠 HARD TRADE VALIDATION (NO SCORING)
# =====================================================
def evaluate_trade_setup(
    symbol: str,
    df,
    price: float,
    mode: str = "INDEX",
    strategy: str = "ORB",
    **kwargs,   # absorbs index_pcr, options_bias, risk_context, etc
) -> Dict:
    """
    HARD validation gate only.

    OUTPUT CONTRACT (LOCKED):
    - allowed: bool
    - block_reason: str | None
    - reasons: list[str]
    - snapshot: dict
    """

    reasons: List[str] = []

    # -------------------------------------------------
    # 1️⃣ BASIC PRICE SANITY (HARD FAIL)
    # -------------------------------------------------
    if price is None or price <= 0:
        return {
            "allowed": False,
            "block_reason": "Invalid or missing live price",
            "reasons": ["Invalid or missing live price"],
            "snapshot": {},
        }

    # -------------------------------------------------
    # 2️⃣ BUILD INDICATOR SNAPSHOT (SAFE)
    # -------------------------------------------------
    snap = _build_indicator_snapshot(df, price)

    # -------------------------------------------------
    # 3️⃣ STRATEGY-SPECIFIC HARD FILTERS
    # -------------------------------------------------
    if strategy == "ORB":
        if snap["vwap"] is not None:
            # Too far from VWAP = poor ORB quality
            if abs(price - snap["vwap"]) / price > 0.01:
                reasons.append(
                    "Price too far from VWAP for clean ORB entry"
                )
        else:
            # VWAP missing is NOT a hard block
            reasons.append(
                "VWAP unavailable (ORB evaluated using price action only)"
            )

    elif strategy == "VWAP_MEAN_REVERSION":
        if snap["vwap"] is None:
            reasons.append(
                "VWAP unavailable for mean reversion strategy"
            )
        else:
            if abs(price - snap["vwap"]) / price < 0.002:
                reasons.append(
                    "Price too close to VWAP, no mean-reversion edge"
                )

    # -------------------------------------------------
    # 4️⃣ RSI EXTREMES (HARD RISK FILTER)
    # -------------------------------------------------
    if snap["rsi"] is not None:
        if snap["rsi"] > 80:
            reasons.append("RSI extremely overbought")
        elif snap["rsi"] < 20:
            reasons.append("RSI extremely oversold")

    # -------------------------------------------------
    # 5️⃣ EMA STRUCTURE FILTER (HARD TREND CHECK)
    # -------------------------------------------------
    if snap["ema_20"] is not None and snap["ema_50"] is not None:
        if snap["ema_20"] < snap["ema_50"]:
            reasons.append(
                "Short-term trend below medium-term EMA"
            )

    # -------------------------------------------------
    # 6️⃣ FINAL HARD DECISION
    # -------------------------------------------------
    allowed = len(reasons) == 0

    return {
        "allowed": allowed,
        "block_reason": reasons[0] if not allowed else None,
        "reasons": reasons,
        "snapshot": snap,
    }