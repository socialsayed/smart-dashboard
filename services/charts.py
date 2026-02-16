import yfinance as yf
import streamlit as st
from config import IST


@st.cache_data(ttl=180)
def get_intraday_data(symbol):
    """
    Fetch intraday OHLC data for NSE stocks.
    Tries 3-minute candles first, falls back to 5-minute.
    ALWAYS returns a tuple: (df, interval)
    """

    try:
        ticker = yf.Ticker(f"{symbol}.NS")

        df = ticker.history(
            period="1d",
            interval="3m",
            auto_adjust=True
        )
        interval = "3m"

        if df is None or df.empty:
            df = ticker.history(
                period="1d",
                interval="5m",
                auto_adjust=True
            )
            interval = "5m"

        if df is None or df.empty:
            return None, None

        df = df.reset_index()

        # Ensure IST timezone
        if df["Datetime"].dt.tz is None:
            df["Datetime"] = (
                df["Datetime"]
                .dt.tz_localize("UTC")
                .dt.tz_convert(IST)
            )
        else:
            df["Datetime"] = df["Datetime"].dt.tz_convert(IST)

        # Keep only current trading day
        latest_date = df["Datetime"].dt.date.max()
        df = df[df["Datetime"].dt.date == latest_date]

        return df, interval

    except Exception:
        # 🚨 ABSOLUTE SAFETY: never break unpacking
        return None, None
