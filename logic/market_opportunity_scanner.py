"""
Canonical Market Opportunity Scanner (BUY / SELL Ready)

RULES:
- Uses SAME validation & confidence logic as app.py
- Direction-aware (BUY / SELL)
- NEVER executes trades
- ML is advisory only
- SAFE for cloud / mobile
"""

from typing import List, Dict
import time

from logic.evaluate_setup import evaluate_trade_setup
from logic.trade_confidence import calculate_trade_confidence, confidence_label

from services.prices import live_price
from services.charts import get_intraday_data
from services.options import get_pcr


# =====================================================
# ⏱ SIMPLE IN-MEMORY THROTTLE (PER RUN)
# =====================================================
_price_cache = {}
_intraday_cache = {}


def _get_price_cached(symbol, ttl=3):
    now = time.time()
    slot = _price_cache.get(symbol)

    if slot and now - slot["ts"] < ttl:
        return slot["value"]

    price, _ = live_price(symbol)
    _price_cache[symbol] = {"value": price, "ts": now}
    return price


def _get_intraday_cached(symbol, ttl=30):
    now = time.time()
    slot = _intraday_cache.get(symbol)

    if slot and now - slot["ts"] < ttl:
        return slot["value"]

    df, _ = get_intraday_data(symbol)
    _intraday_cache[symbol] = {"value": df, "ts": now}
    return df


# =====================================================
# MAIN SCANNER ENTRY POINT
# =====================================================
def run_market_opportunity_scanner(
    symbols: List[str],
    strategy: str = "ORB",
    direction: str = "BUY",
) -> List[Dict]:

    results = []

    # Fetch index PCR ONCE
    try:
        index_pcr = get_pcr()
    except Exception:
        index_pcr = None

    for symbol in symbols:
        try:
            # -------------------------------
            # 1️⃣ LIVE PRICE (THROTTLED)
            # -------------------------------
            price = _get_price_cached(symbol)
            if price is None:
                continue

            # -------------------------------
            # 2️⃣ INTRADAY DATA (THROTTLED)
            # -------------------------------
            df = _get_intraday_cached(symbol)

            # -------------------------------
            # 3️⃣ HARD VALIDATION
            # -------------------------------
            validation = evaluate_trade_setup(
                symbol=symbol,
                df=df,
                price=price,
                strategy=strategy,
                mode="SCANNER",
            )

            if not validation["allowed"]:
                results.append({
                    "symbol": symbol,
                    "status": "AVOID",
                    "confidence": "NO_TRADE",
                    "confidence_score": 0,
                    "reasons": validation.get("reasons", []),
                })
                continue

            snapshot = validation.get("snapshot", {})

            # -------------------------------
            # 4️⃣ CONFIDENCE SCORING (DIRECTION-AWARE)
            # -------------------------------
            score, score_reasons = calculate_trade_confidence(
                snapshot=snapshot,
                price=price,
                direction=direction,
                index_pcr=index_pcr,
                options_bias="NEUTRAL",
                risk_context=None,
            )

            label = confidence_label(score)

            # -------------------------------
            # 5️⃣ MAP TO SCANNER STATUS
            # -------------------------------
            if score >= 75:
                status = "BUY" if direction == "BUY" else "SELL"
            elif score >= 55:
                status = "WATCH"
            else:
                status = "AVOID"

            results.append({
                "symbol": symbol,
                "status": status,
                "confidence": label,
                "confidence_score": score,
                "reasons": score_reasons,
            })

        except Exception:
            continue

    return results