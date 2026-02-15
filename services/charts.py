import yfinance as yf
import pandas as pd
import streamlit as st
from config import IST

@st.cache_data(ttl=180)
def get_intraday_data(symbol, interval="3m"):
    ticker = yf.Ticker(f"{symbol}.NS")

    df = ticker.history(
        period="5d",
        interval=interval,
        auto_adjust=True
    )

    if df.empty:
        return None

    df = df.reset_index()
    df["Datetime"] = df["Datetime"].dt.tz_convert(IST)

    today = df["Datetime"].dt.date.iloc[-1]
    df = df[df["Datetime"].dt.date == today]

    return df if not df.empty else None
