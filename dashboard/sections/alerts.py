# =====================================================
# ALERTS SECTION
# Extracted from app.py – STEP A1.6
# =====================================================

import streamlit as st


def render_alerts_section(price, section_help):
    """
    Price + Level based alerts.
    Must behave IDENTICALLY to original implementation.
    """

    alerts = []

    levels = st.session_state.get("levels", {})

    if price and levels:
        if price > levels.get("orb_high", float("inf")):
            alerts.append("📈 ORB High Breakout")

        if price < levels.get("orb_low", 0):
            alerts.append("📉 ORB Low Breakdown")

        if abs(price - levels.get("support", price)) / price < 0.002:
            alerts.append("🟢 Near Support")

        if abs(price - levels.get("resistance", price)) / price < 0.002:
            alerts.append("🔴 Near Resistance")

    new_alerts = []

    for a in alerts:
        if a not in st.session_state.alert_state:
            new_alerts.append(a)
            st.session_state.alert_state.add(a)

    if new_alerts:
        st.subheader(
            "🔔 Alerts",
            help=section_help["alerts"]
        )
        for a in new_alerts:
            st.warning(a)