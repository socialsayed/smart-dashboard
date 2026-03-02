# =====================================================
# INTRADAY UTILITIES
# =====================================================

import pandas as pd
import streamlit as st


def detect_live_support(df: pd.DataFrame, lookback=3):
    if df is None or len(df) < lookback * 2 + 1:
        return None

    lows = df["Low"].values
    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        if (
            lows[i] < min(lows[i - lookback:i]) and
            lows[i] < min(lows[i + 1:i + lookback + 1])
        ):
            swing_lows.append(lows[i])

    if not swing_lows:
        return None

    current_price = df["Close"].iloc[-1]
    valid = [l for l in swing_lows if l < current_price]

    return max(valid) if valid else None


def detect_live_resistance(df: pd.DataFrame, lookback=3):
    if df is None or len(df) < lookback * 2 + 1:
        return None

    highs = df["High"].values
    swing_highs = []

    for i in range(lookback, len(df) - lookback):
        if (
            highs[i] > max(highs[i - lookback:i]) and
            highs[i] > max(highs[i + 1:i + lookback + 1])
        ):
            swing_highs.append(highs[i])

    if not swing_highs:
        return None

    current_price = df["Close"].iloc[-1]
    valid = [h for h in swing_highs if h > current_price]

    return min(valid) if valid else None


def sanity_check_intraday(df, interval, symbol):
    if df is None or df.empty:
        st.warning(f"⚠️ {symbol}: Intraday data unavailable")
        return False

    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        st.warning(f"⚠️ Missing OHLC columns: {missing}")
        return False

    if not hasattr(df.index, "is_monotonic_increasing") or not df.index.is_monotonic_increasing:
        st.warning("⚠️ Intraday candles not time-sorted")

    if df[list(required)].isna().mean().mean() > 0.25:
        st.warning("⚠️ High NaN density in intraday candles")

    if df.iloc[-1][list(required)].isna().any():
        st.warning("⚠️ Latest candle incomplete (live candle)")

    if interval is not None:
        allowed_intervals = {"1m", "2m", "3m", "5m", "15m", "30m", "60m"}
        if interval not in allowed_intervals:
            st.warning(f"⚠️ Unsupported interval: {interval}")

    return True