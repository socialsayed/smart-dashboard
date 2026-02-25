import yfinance as yf
import streamlit as st
from config import IST


@st.cache_data(ttl=180)
def get_intraday_data(symbol):
    """
    Fetch intraday OHLC data with safe fallback intervals.
    Returns (df, interval) or (None, None)
    """
    import yfinance as yf

    if not symbol:
        return None, None

    ticker = yf.Ticker(f"{symbol}.NS")

    # --- Try preferred intervals in order ---
    attempts = [
        ("3m", "1d"),
        ("5m", "1d"),
        ("1m", "1d"),   # last resort
    ]

    for interval, period in attempts:
        try:
            df = ticker.history(interval=interval, period=period)
            if df is not None and not df.empty:
                df = df.rename(columns=str.title)
                return df, interval
        except Exception:
            continue

    # --- Total failure ---
    return None, None