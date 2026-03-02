import streamlit as st


def render_levels_section(
    price,
    section_help,
    calc_levels,
    detect_live_support,
    detect_live_resistance,
):
    """
    Support & Resistance + Live Context block.
    Clean injection.
    No hidden dependencies.
    """

    st.subheader(
        "📌 Live Support & Resistance",
        help=section_help["support_resistance"]
    )

    # ----------------------------------------
    # Ensure levels always exist
    # ----------------------------------------
    levels = st.session_state.get("levels", {})
    last_price = st.session_state.get("last_price")

    if price and price != last_price:
        levels = calc_levels(price)
        st.session_state.levels = levels
        st.session_state.last_price = price

    # ----------------------------------------
    # Live structure detection
    # ----------------------------------------
    live_support = None
    live_resistance = None

    if st.session_state.get("last_intraday_df") is not None:
        live_support = detect_live_support(
            st.session_state.last_intraday_df
        )
        live_resistance = detect_live_resistance(
            st.session_state.last_intraday_df
        )

    # ----------------------------------------
    # Metrics display
    # ----------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Support", levels.get("support", "—"))
    c2.metric("Resistance", levels.get("resistance", "—"))
    c3.metric("ORB High", levels.get("orb_high", "—"))
    c4.metric("ORB Low", levels.get("orb_low", "—"))
    c5.metric(
        "Live Resistance",
        f"{live_resistance:.2f}" if live_resistance else "—",
        help="Auto-detected from intraday swing highs"
    )

    # ----------------------------------------
    # Context messages
    # ----------------------------------------
    context_msgs = []

    if price and levels and all(
        k in levels for k in ("support", "resistance", "orb_high", "orb_low")
    ):
        if abs(price - levels["resistance"]) / price < 0.003:
            context_msgs.append(
                "⚠️ Price near resistance — breakout or rejection zone."
            )
        if abs(price - levels["support"]) / price < 0.003:
            context_msgs.append(
                "🟢 Price near support — potential demand zone."
            )
        if price > levels["orb_high"]:
            context_msgs.append(
                "📈 Above ORB High — bullish momentum."
            )
        if price < levels["orb_low"]:
            context_msgs.append(
                "📉 Below ORB Low — bearish momentum."
            )

    if not context_msgs:
        context_msgs.append(
            "ℹ️ Price is between key intraday levels."
        )

    with st.expander("ℹ️ Live Level Context (Auto-updating)"):
        for msg in context_msgs:
            st.markdown(f"- {msg}")

    st.divider()