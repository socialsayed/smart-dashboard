# =====================================================
# 🔎 MARKET SCANNER ENGINE
# VERSION: SIDB-v2.6.0 (ADD-ON, NON-BREAKING)
# PURPOSE: Unified scanner for NIFTY50 / BANKNIFTY /
#          daily_watchlist / manual stock
# =====================================================

import time
from typing import List, Dict

import streamlit as st

# --- Reuse existing core logic ---
from utils.market import market_status
from utils.intraday import cached_intraday_data
from utils.indicators import compute_vwap, compute_orb_levels
from logic.trade_confidence import calculate_trade_confidence
from logic.trade_decision import trade_decision_engine


# =====================================================
# CONFIG
# =====================================================
SCANNER_THROTTLE_SECONDS = 300  # 5 minutes
BUY_CONFIDENCE_THRESHOLD = 70


# =====================================================
# INTERNAL STATE (SESSION)
# =====================================================
def _init_scanner_state():
    if "last_scanner_run_ts" not in st.session_state:
        st.session_state.last_scanner_run_ts = 0

    if "scanner_alerts" not in st.session_state:
        st.session_state.scanner_alerts = []


# =====================================================
# CORE SCANNER
# =====================================================
def run_market_scanner(symbols: List[str]) -> List[Dict]:
    """
    Runs the SAME analysis pipeline used by inbuilt lists
    on ANY list of symbols.

    Returns:
        List of alert dicts (BUY / WATCH / AVOID)
    """
    _init_scanner_state()

    open_now, _ = market_status()
    now = time.time()

    # --- Do not scan if market closed ---
    if not open_now:
        return []

    # --- Throttle scanner ---
    if now - st.session_state.last_scanner_run_ts < SCANNER_THROTTLE_SECONDS:
        return []

    st.session_state.last_scanner_run_ts = now

    alerts = []

    for symbol in symbols:
        try:
            # ---------------------------------------------
            # Fetch intraday data (cached)
            # ---------------------------------------------
            df, interval = cached_intraday_data(symbol)

            if df is None or df.empty:
                continue

            # ---------------------------------------------
            # Indicators
            # ---------------------------------------------
            vwap_df = compute_vwap(df)
            orb_high, orb_low = compute_orb_levels(df)

            # ---------------------------------------------
            # Confidence Engine (existing)
            # ---------------------------------------------
            confidence = calculate_trade_confidence(
                df=df,
                vwap_df=vwap_df,
                orb_high=orb_high,
                orb_low=orb_low,
            )

            # ---------------------------------------------
            # Trade Decision Engine (existing)
            # ---------------------------------------------
            decision = trade_decision_engine(
                symbol=symbol,
                confidence=confidence,
                df=df,
                vwap_df=vwap_df,
                orb_high=orb_high,
                orb_low=orb_low,
            )

            # ---------------------------------------------
            # ALERT LOGIC (NO OPINION)
            # ---------------------------------------------
            if decision["allowed"] and confidence >= BUY_CONFIDENCE_THRESHOLD:
                alerts.append({
                    "type": "BUY",
                    "symbol": symbol,
                    "confidence": confidence,
                    "reason": decision["reason"],
                })

            elif not decision["allowed"]:
                alerts.append({
                    "type": "AVOID",
                    "symbol": symbol,
                    "confidence": confidence,
                    "reason": decision["reason"],
                })

            else:
                alerts.append({
                    "type": "WATCH",
                    "symbol": symbol,
                    "confidence": confidence,
                    "reason": "Setup forming",
                })

        except Exception as e:
            # Fail-safe: scanner should never crash app
            continue

    # Persist alerts (for UI rendering)
    st.session_state.scanner_alerts = alerts

    return alerts