# =====================================================
# TRADE ANALYTICS SECTION
# Extracted from app.py – STEP A1.10
# =====================================================

import streamlit as st
import pandas as pd
from services.market_time import now_ist
from config.subscription import DEFAULT_USER_TIER, get_tier_config


def render_trade_analytics_section():
    """
    Renders trade analytics dashboard.
    Must behave IDENTICALLY to original implementation.
    """

    user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
    tier_cfg = get_tier_config(user_tier)
    history_days = tier_cfg.get("history_days")

    st.subheader("📊 Trade Analytics")

    all_closed_trades = [
        t for t in st.session_state.history
        if t.get("Status") == "CLOSED"
        and isinstance(t.get("PnL"), (int, float))
    ]

    if history_days is not None:
        cutoff_date = now_ist().date() - pd.Timedelta(days=history_days - 1)

        filtered_trades = []
        for t in all_closed_trades:
            try:
                trade_date = pd.to_datetime(t.get("Date")).date()
                if trade_date >= cutoff_date:
                    filtered_trades.append(t)
            except Exception:
                continue
    else:
        filtered_trades = all_closed_trades

    if filtered_trades:
        df_trades = pd.DataFrame(filtered_trades)
    else:
        df_trades = pd.DataFrame(columns=["PnL", "Strategy", "Entry Time"])

    if history_days is not None and history_days > 1:
        st.caption(
            f"ℹ️ Showing last **{history_days} days** of trade history "
            f"(based on your access level)."
        )
    elif history_days == 1:
        st.caption(
            "ℹ️ Showing **today’s trades only** based on current access level. "
            "Extended historical analytics provide educational review context."
        )

    if not df_trades.empty:
        total_trades = len(df_trades)
        wins = df_trades[df_trades["PnL"] > 0]
        losses = df_trades[df_trades["PnL"] < 0]

        win_rate = (len(wins) / total_trades) * 100 if total_trades else 0.0
        avg_win = wins["PnL"].mean() if not wins.empty else 0.0
        avg_loss = losses["PnL"].mean() if not losses.empty else 0.0

        expectancy = (
            (win_rate / 100) * avg_win +
            (1 - win_rate / 100) * avg_loss
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", total_trades)
        c2.metric("Win Rate %", f"{win_rate:.1f}%")
        c3.metric("Avg Win (₹)", f"{avg_win:.2f}")
        c4.metric("Avg Loss (₹)", f"{avg_loss:.2f}")

        st.metric("📐 Expectancy (₹ / trade)", f"{expectancy:.2f}")
    else:
        st.info("ℹ️ No closed trades available in the current history window.")

    st.subheader("📈 Strategy-wise PnL")

    if not df_trades.empty:
        strat_df = (
            df_trades.groupby("Strategy", as_index=False)["PnL"]
            .sum()
            .sort_values("PnL", ascending=False)
        )

        st.dataframe(strat_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Strategy performance will appear after trades are CLOSED.")

    st.subheader("⏱ Time-of-Day Performance")

    if not df_trades.empty and "Entry Time" in df_trades.columns:
        df_trades["Hour"] = pd.to_datetime(
            df_trades["Entry Time"],
            format="%H:%M:%S",
            errors="coerce"
        ).dt.hour

        hour_pnl = (
            df_trades.groupby("Hour", as_index=False)["PnL"]
            .sum()
            .rename(columns={"PnL": "Total PnL"})
        )

        st.dataframe(hour_pnl, use_container_width=True)
    else:
        st.info("ℹ️ Time-based stats will appear after trades are CLOSED.")

    st.subheader("📘 How to Use This Dashboard")

    with st.expander("Click to read"):
        st.markdown("""
• Pre-market → mark bias & levels  
• First 15 min → observe ORB  
• Trade only with confirmation  
• Respect daily risk limits  
• Review, don't revenge trade  
""")