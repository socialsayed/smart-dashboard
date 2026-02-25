"""
Trade setup evaluation logic.
Used by app.py to validate trade conditions and build context snapshots.

IMPORTANT DESIGN RULE:
- Indicators are OPTIONAL
- Validation must NEVER crash
- Output contract is FROZEN
"""

from typing import Dict, List


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


def evaluate_trade_setup(
    symbol: str,
    df,
    price: float,
    mode: str = "INDEX",
    strategy: str = "ORB",
    **kwargs,   # absorbs index_pcr, stock_pcr, etc
) -> Dict:
    """
    Evaluate whether a trade setup is valid.

    OUTPUT CONTRACT (DO NOT BREAK):
    - allowed: bool
    - confidence: int (0–100)
    - confidence_label: str
    - reasons: list[str]
    - snapshot: dict
    """

    reasons: List[str] = []

    # --- Basic sanity check ---
    if price is None or price <= 0:
        return {
            "allowed": False,
            "confidence": 0,
            "confidence_label": "LOW",
            "is_valid": False,
            "reasons": ["Invalid or missing live price"],
            "snapshot": {},
        }

    # --- Indicators (safe) ---
    snap = _build_indicator_snapshot(df, price)

    # --- Strategy logic ---
    if strategy == "ORB":
        if snap["vwap"] is not None:
            if abs(price - snap["vwap"]) / price > 0.01:
                reasons.append("Price too far from VWAP for clean ORB entry")
        else:
            reasons.append("VWAP unavailable (using price action only)")

    elif strategy == "VWAP_MEAN_REVERSION":
        if snap["vwap"] is None:
            reasons.append("VWAP unavailable for mean reversion strategy")
        else:
            if abs(price - snap["vwap"]) / price < 0.002:
                reasons.append("Price too close to VWAP, no edge")

    # --- Optional filters ---
    if snap["rsi"] is not None:
        if snap["rsi"] > 80:
            reasons.append("RSI extremely overbought")
        elif snap["rsi"] < 20:
            reasons.append("RSI extremely oversold")

    if snap["ema_20"] is not None and snap["ema_50"] is not None:
        if snap["ema_20"] < snap["ema_50"]:
            reasons.append("Short-term trend below medium-term EMA")

    # --- Final decision ---
    is_valid = len(reasons) == 0
    confidence_score = 100 if is_valid else 0

    if confidence_score >= 80:
        confidence_label = "HIGH"
    elif confidence_score >= 50:
        confidence_label = "MEDIUM"
    else:
        confidence_label = "LOW"

    return {
        "allowed": is_valid,
        "confidence": confidence_score,
        "confidence_label": confidence_label,
        "is_valid": is_valid,
        "reasons": reasons,
        "snapshot": snap,
    }