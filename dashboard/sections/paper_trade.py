# =====================================================
# PAPER TRADE SECTION
# =====================================================

import streamlit as st
import pandas as pd


def render_paper_trade_section(
    stock,
    strategy,
    allowed,
    block_reason,
    options_bias,
    now_ist,
    get_live_price_fast,   # kept for compatibility (not used for open trades)
    load_day_trades,
    append_trade,
    update_trade_in_csv,
    generate_trade_id,
    refresh_risk_from_history,
):

    # -------------------------------------------------
    # Ensure session history exists (safety fallback)
    # -------------------------------------------------
    if "history" not in st.session_state:
        st.session_state.history = load_day_trades()

    st.subheader("🧪 Paper Trade Simulator (Educational Only)")

    ltp = st.session_state.get("last_price_metric")

    qty = st.number_input(
        "Quantity (Lots / Units)",
        min_value=1,
        step=1,
        key="paper_qty"
    )

    col1, col2 = st.columns(2)

    # =====================================================
    # OPEN POSITION
    # =====================================================
    with col1:

        action_label = (
            "📈 Simulate BUY (Long)"
            if st.session_state.direction == "BUY"
            else "📉 Simulate SELL (Short)"
        )

        if st.button(action_label, use_container_width=True):

            if not allowed:
                st.error(f"❌ Trade blocked: {block_reason}")

            elif ltp is None:
                st.error("❌ Live price unavailable.")

            else:
                trade_id = generate_trade_id()
                entry_time = now_ist().strftime("%H:%M:%S")

                trade_row = {
                    "Trade ID": trade_id,
                    "Date": now_ist().date().isoformat(),
                    "Symbol": stock,
                    "Side": st.session_state.direction,
                    "Entry": round(ltp, 2),
                    "Exit": None,
                    "Qty": qty,
                    "PnL": 0.0,
                    "Entry Time": entry_time,
                    "Exit Time": None,
                    "Strategy": strategy,
                    "Options Bias": options_bias,
                    "Market Status": "OPEN",
                    "Notes": "",
                    "Status": "OPEN",
                }

                append_trade(trade_row)

                # 🔥 Sync session memory immediately
                st.session_state.history = load_day_trades()
                refresh_risk_from_history()

                st.success(
                    f"{action_label} recorded | {stock} @ {ltp} (Paper Trade)"
                )

    with col2:
        st.info("Use inline Exit buttons to close positions.")

    st.divider()

    # =====================================================
    # 🟢 OPEN TRADES (INLINE EXIT TABLE)
    # =====================================================
    st.subheader("🟢 Open Trades")

    trades_today = st.session_state.history
    open_trades = [t for t in trades_today if t["Status"] == "OPEN"]

    if not open_trades:
        st.info("No open trades.")
    else:

        headers = [
            "Trade ID", "Date", "Symbol", "Side", "Entry",
            "Exit", "Qty", "PnL", "Entry Time", "Exit Time",
            "Strategy", "Options Bias", "Market Status",
            "Notes", "Status", "Action"
        ]

        header_cols = st.columns(len(headers))
        for col, title in zip(header_cols, headers):
            col.markdown(f"**{title}**")

        st.divider()

        current_price = st.session_state.get("last_price_metric")

        for trade in open_trades:

            # 🔥 Reuse already polled price (no extra API calls)
            trade_price = current_price

            if trade_price is not None:
                if trade["Side"] == "BUY":
                    pnl = round((trade_price - trade["Entry"]) * trade["Qty"], 2)
                else:
                    pnl = round((trade["Entry"] - trade_price) * trade["Qty"], 2)
            else:
                pnl = 0.0

            row_cols = st.columns(len(headers))

            values = [
                trade["Trade ID"],
                trade["Date"],
                trade["Symbol"],
                trade["Side"],
                trade["Entry"],
                None,
                trade["Qty"],
                pnl,
                trade["Entry Time"],
                None,
                trade["Strategy"],
                trade["Options Bias"],
                trade["Market Status"],
                trade["Notes"],
                trade["Status"],
            ]

            for col, val in zip(row_cols[:-1], values):
                col.write(val)

            # ---- Inline Exit Button ----
            if row_cols[-1].button(
                "❌ Exit",
                key=f"exit_inline_{trade['Trade ID']}"
            ):

                if trade_price is None:
                    st.error("Live price unavailable.")
                    st.stop()

                exit_time = now_ist().strftime("%H:%M:%S")

                update_trade_in_csv(
                    trade["Trade ID"],
                    {
                        "Exit": trade_price,
                        "PnL": pnl,
                        "Exit Time": exit_time,
                        "Status": "CLOSED",
                    }
                )

                # 🔥 Sync session after closing
                st.session_state.history = load_day_trades()
                refresh_risk_from_history()

                st.success(f"Closed {trade['Symbol']} | PnL ₹{pnl}")
                st.rerun()

            st.divider()

    # =====================================================
    # 🔵 CLOSED TRADES
    # =====================================================
    st.subheader("🔵 Closed Trades")

    closed_trades = [
        t for t in st.session_state.history
        if t["Status"] == "CLOSED"
    ]

    if closed_trades:
        st.dataframe(pd.DataFrame(closed_trades), use_container_width=True)
    else:
        st.info("No closed trades yet.")