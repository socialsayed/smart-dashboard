# =====================================================
# MARKET OPPORTUNITY SCANNER (FROZEN BASELINE v1)
# Mirrors app.py trade logic EXACTLY
# =====================================================

from services.prices import live_price
from services.charts import get_intraday_data
from logic.decision import calculate_trade_confidence, confidence_label
from logic.levels import calc_levels
from services.options import get_pcr


def normalize_symbol(symbol: str) -> str:
    """
    Accepts manual input like:
    TCS, RELIANCE, INFY
    Returns normalized NSE symbol
    """
    symbol = symbol.upper().strip()
    return symbol.replace(".NS", "")


def run_market_opportunity_scanner(symbols):
    results = []

    if not symbols:
        return results

    index_pcr = get_pcr()

    for raw_symbol in symbols:
        symbol = normalize_symbol(raw_symbol)

        try:
            # -----------------------------
            # LIVE PRICE (same as app)
            # -----------------------------
            price, src = live_price(symbol)
            if price is None:
                results.append({
                    "symbol": symbol,
                    "status": "AVOID",
                    "confidence": 0,
                    "reasons": ["Live price unavailable"]
                })
                continue

            # -----------------------------
            # INTRADAY DATA
            # -----------------------------
            df, interval = get_intraday_data(symbol)
            if df is None or df.empty:
                results.append({
                    "symbol": symbol,
                    "status": "AVOID",
                    "confidence": 0,
                    "reasons": ["Intraday data unavailable"]
                })
                continue

            # -----------------------------
            # LEVELS (same as app)
            # -----------------------------
            levels = calc_levels(price)

            # -----------------------------
            # VWAP + TREND (same logic)
            # -----------------------------
            vwap = df["VWAP"].iloc[-1]

            vwap_series = df["VWAP"].tail(5)
            if len(vwap_series) >= 2:
                vwap_slope = (vwap_series.iloc[-1] - vwap_series.iloc[0]) / vwap
            else:
                vwap_slope = 0

            highs = df["High"].tail(5)
            lows = df["Low"].tail(5)

            higher_highs = sum(highs.diff().dropna() > 0)
            higher_lows = sum(lows.diff().dropna() > 0)

            if higher_highs >= 3 and higher_lows >= 3:
                trend_alignment = "STRONG"
            elif higher_highs >= 2:
                trend_alignment = "MILD"
            else:
                trend_alignment = "NONE"

            # -----------------------------
            # ORB SIGNAL
            # -----------------------------
            orb_signal = (
                "CONFIRMED"
                if price > levels.get("orb_high", float("inf"))
                else "NONE"
            )

            # -----------------------------
            # CONFIDENCE (shared engine)
            # -----------------------------
            confidence_score, reasons_map = calculate_trade_confidence({
                "price": price,
                "vwap": vwap,
                "vwap_slope": vwap_slope,
                "orb_signal": orb_signal,
                "trend_alignment": trend_alignment,
                "pcr": index_pcr,
                "direction": "BUY"
            })

            label = confidence_label(confidence_score)

            # -----------------------------
            # FINAL CLASSIFICATION
            # -----------------------------
            if confidence_score >= 70:
                status = "BUY"
            elif confidence_score >= 45:
                status = "WATCH"
            else:
                status = "AVOID"

            results.append({
                "symbol": symbol,
                "status": status,
                "confidence": confidence_score,
                "reasons": list(reasons_map.values())
            })

        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "AVOID",
                "confidence": 0,
                "reasons": [f"Scanner error: {e}"]
            })

    return results