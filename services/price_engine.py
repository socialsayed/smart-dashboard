# =====================================================
# LIVE PRICE ENGINE (HARDENED – P3-4)
# =====================================================

import time
import requests
import streamlit as st
import logging
from datetime import datetime
from services.prices import live_price

logger = logging.getLogger("SIDB")


def get_live_price_fast(symbol, min_interval=1.5):
    """
    Fetch live price via shared data service.
    Tracks server timestamp for freshness labeling.
    """

    key = f"_fast_price_{symbol}"

    if key not in st.session_state:
        st.session_state[key] = {
            "ts": None,
            "poll_ts": 0,
            "price": None,
            "src": None,
        }

    slot = st.session_state[key]
    now = time.time()

    if now - slot["poll_ts"] >= min_interval:

        # ---- Attempt shared backend first ----
        try:
            resp = requests.get(
                f"http://127.0.0.1:8000/price/{symbol}",
                timeout=0.8
            )

            if resp.status_code == 200:
                data = resp.json()
                slot["price"] = data.get("price")
                slot["src"] = "SHARED_LIVE"

                ts = data.get("timestamp")
                if ts:
                    slot["ts"] = datetime.fromisoformat(ts).timestamp()

            else:
                logger.warning(
                    f"Shared service HTTP {resp.status_code} for {symbol}"
                )
                raise RuntimeError("Shared service error")

        except requests.Timeout:
            logger.warning(f"Shared service timeout for {symbol}")

        except Exception:
            logger.exception(f"Shared service failure for {symbol}")

        # ---- Fallback to direct price ----
        if slot["price"] is None:
            try:
                slot["price"], slot["src"] = live_price(symbol)
                slot["ts"] = time.time()

                if slot["price"] is not None:
                    logger.info(f"Direct price fallback used for {symbol}")

            except Exception:
                logger.exception(f"Direct fallback price failure for {symbol}")

        slot["poll_ts"] = now

    return slot["price"], slot["src"]


def price_freshness_label(price_ts):
    if not price_ts:
        return "DELAYED", "🔴", None

    age = time.time() - price_ts

    if age <= 3:
        return "LIVE", "🟢", int(age)
    if age <= 15:
        return "NEAR-LIVE", "🟡", int(age)

    return "DELAYED", "🔴", int(age)


def poll_price(symbol):
    price, src = get_live_price_fast(symbol)

    if price is not None:
        st.session_state.last_price_metric = price

    return price, src


def background_refresh(symbol, open_now, cached_intraday_data,
                       cached_add_vwap, cached_index_pcr):
    """
    Refresh heavy data WITHOUT touching UI.
    """

    now = time.time()

    # ---- Intraday data ----
    if now - st.session_state.get("last_intraday_refresh", 0) > 30:
        try:
            df, interval = cached_intraday_data(symbol)

            if df is not None and not df.empty:
                df = cached_add_vwap(df)
                st.session_state.last_intraday_df = df
            else:
                logger.warning(f"Intraday data empty for {symbol}")

        except Exception:
            logger.exception(f"Intraday refresh failed for {symbol}")

        st.session_state.last_intraday_refresh = now

    # ---- Index PCR ----
    if now - st.session_state.get("last_pcr_refresh", 0) > 30:
        try:
            st.session_state.cached_index_pcr = cached_index_pcr()

        except Exception:
            logger.exception("Index PCR refresh failed")

        st.session_state.last_pcr_refresh = now