# =====================================================
# TRADE PERSISTENCE ENGINE
# Extracted from app.py – STAGE A2.1
# =====================================================

import os
import time
import pandas as pd
import streamlit as st
from services.market_time import now_ist


PAPER_TRADE_DIR = "data/paper_trades"


def get_trade_date():
    return now_ist().date().isoformat()


def get_trade_file():
    os.makedirs(PAPER_TRADE_DIR, exist_ok=True)
    return os.path.join(PAPER_TRADE_DIR, f"{get_trade_date()}.csv")


def load_day_trades():
    path = get_trade_file()

    if not os.path.exists(path):
        return []

    try:
        df = pd.read_csv(
            path,
            engine="python",
            on_bad_lines="skip"
        )
    except Exception as e:
        st.error(f"⚠️ Paper trade CSV corrupted: {e}")
        return []

    expected_cols = [
        "Trade ID",
        "Date",
        "Symbol",
        "Side",
        "Entry",
        "Exit",
        "Qty",
        "PnL",
        "Entry Time",
        "Exit Time",
        "Strategy",
        "Options Bias",
        "Market Status",
        "Notes",
        "Status",
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df = df[expected_cols]

    return df.to_dict("records")


def append_trade(row: dict):
    path = get_trade_file()
    df = pd.DataFrame([row])
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", header=header, index=False)


def update_trade_in_csv(trade_id: str, updates: dict):
    path = get_trade_file()
    if not os.path.exists(path):
        return

    df = pd.read_csv(path)

    if "Trade ID" not in df.columns:
        return

    mask = df["Trade ID"] == trade_id
    if not mask.any():
        return

    for k, v in updates.items():
        if k in df.columns:
            df.loc[mask, k] = v

    df.to_csv(path, index=False)


def generate_trade_id():
    return f"T{int(time.time() * 1000)}"


def refresh_risk_from_history():
    closed = [
        t for t in st.session_state.history
        if t["Status"] == "CLOSED" and isinstance(t.get("PnL"), (int, float))
    ]
    st.session_state.trades = len(closed)
    st.session_state.pnl = sum(t["PnL"] for t in closed)