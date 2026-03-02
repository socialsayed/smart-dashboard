# =====================================================
# ML ADVISORY SECTION (HARD-GATED – PHASE 4 P4-2)
# =====================================================

import streamlit as st
from config.subscription import DEFAULT_USER_TIER, get_tier_config
from services.access_control import AccessControl


def render_ml_advisory_section():
    """
    Renders ML historical advisory block.
    Must behave IDENTICALLY to original implementation
    for allowed tiers.
    """

    # -------------------------------------------------
    # ACCESS CONTROL (HARD ENFORCEMENT)
    # -------------------------------------------------
    access = AccessControl()
    access.validate()

    # Hard block: if tier does not allow ML, do nothing
    if not access.can_ml_advisory:
        return

    # ---- Subscription context (kept for explanation gating only) ----
    user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
    tier_cfg = get_tier_config(user_tier)

    CAN_VIEW_ML_EXPLANATION = tier_cfg.get("show_ml_explanation", False)

    ml_score = st.session_state.get("ml_score")
    ml_reasons = st.session_state.get("ml_reasons", [])

    if ml_score is not None:
        ml_pct = int(ml_score * 100)

        # --- ALWAYS visible for allowed tiers ---
        st.info(
            f"🤖 **ML Setup Quality (Educational Context Only)**\n\n"
            f"- Historical similarity score: **{ml_pct}/100**\n"
            f"- Derived from past market behavior patterns\n\n"
            f"ℹ️ This score is **not predictive** and **not a recommendation**.\n"
            f"ℹ️ It does not permit, block, or suggest trades.\n"
            f"✔ Final eligibility is always determined by rule-based validation."
        )

        # --- Explanation gating (advanced tiers only) ---
        if CAN_VIEW_ML_EXPLANATION and ml_reasons:
            with st.expander("🔍 ML Factor Breakdown (Educational)"):
                for r in ml_reasons:
                    st.write(f"- {r}")

        elif not CAN_VIEW_ML_EXPLANATION:
            st.caption(
                "ℹ️ ML factor-level explanations are available for advanced users. "
                "They provide historical context only — not predictions or advice."
            )