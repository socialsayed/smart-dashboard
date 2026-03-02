# =====================================================
# TRADE DECISION SECTION
# Extracted from app.py – STEP A1.7
# =====================================================

import streamlit as st
from config.subscription import DEFAULT_USER_TIER, get_tier_config
from logic.trade_confidence import calculate_trade_confidence, confidence_label
from logic.evaluate_setup import evaluate_trade_setup


def render_trade_decision_section(
    stock,
    strategy,
    price,
    index_pcr,
    options_bias,
):
    """
    Renders rule validation + confidence engine.
    Must behave IDENTICALLY to original implementation.
    """

    # --- HARD VALIDATION (RULE GATE) ---
    validation = evaluate_trade_setup(
        symbol=stock,
        df=st.session_state.last_intraday_df,
        price=price,
        strategy="ORB" if strategy == "ORB Breakout" else "VWAP_MEAN_REVERSION",
        mode="MANUAL",
    )

    allowed = validation["allowed"]
    block_reason = validation.get("block_reason")
    reasons = validation.get("reasons", [])
    snapshot = validation.get("snapshot", {})

    confidence_score = 0
    confidence_label_text = "NO_TRADE"
    confidence_reasons = []

    # --- CONFIDENCE SCORING ---
    if allowed and price is not None:
        confidence_score, confidence_reasons = calculate_trade_confidence(
            snapshot=snapshot,
            price=price,
            direction=st.session_state.direction,
            index_pcr=index_pcr,
            options_bias=options_bias,
            risk_context={
                "trades": st.session_state.trades,
                "pnl": st.session_state.pnl,
            },
        )
        confidence_label_text = confidence_label(confidence_score)

    # --- Subscription Context ---
    user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
    tier_cfg = get_tier_config(user_tier)

    # --- UI Output ---
    if allowed:

        if user_tier == "FREE":
            st.success(
                f"✅ Setup Eligible (Rules Passed) | "
                f"Quality: {confidence_label_text}"
            )
            st.caption(
                "ℹ️ Numerical setup quality scores and breakdown are available "
                "at higher access levels. Educational context only."
            )

        elif user_tier == "BASIC":
            st.success(
                f"✅ Setup Eligible (Rules Passed) | "
                f"Quality Score: {confidence_score}/100 ({confidence_label_text})"
            )

        elif user_tier in ["PRO", "ELITE"]:
            st.success(
                f"✅ Setup Eligible (Rules Passed) | "
                f"Quality Score: {confidence_score}/100 ({confidence_label_text})"
            )

    else:
        st.error(
            f"🚫 Setup Ineligible (Rules Failed) | Reason: {block_reason}"
        )

    # --- Why This Decision ---
    if reasons or confidence_reasons:
        with st.expander("📌 Why this evaluation? (Rule & Context Breakdown)"):
            if reasons:
                st.markdown("**Rule Validation:**")
                for r in reasons:
                    st.write(f"- {r}")

            if confidence_reasons:
                st.markdown("**Setup Quality Factors (Non-Predictive):**")
                for r in confidence_reasons:
                    st.write(f"- {r}")

    return allowed, block_reason