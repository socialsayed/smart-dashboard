import streamlit as st
import config
from config.subscription import DEFAULT_USER_TIER, get_tier_config


def render_sidebar():
    """
    Renders entire sidebar and returns context dictionary.
    Handles:
    - Index mode
    - Manual mode
    - Scanner reset on mode change
    - Scanner reset on stock change
    - Regulatory-safe captions
    """

    # =====================================================
    # SESSION DEFAULTS
    # =====================================================
    st.session_state.setdefault("index", list(config.INDEX_MAP.keys())[0])
    st.session_state.setdefault(
        "stock",
        config.INDEX_MAP[st.session_state.index][0]
    )
    st.session_state.setdefault("strategy", "ORB Breakout")
    st.session_state.setdefault("max_trades", 1000)
    st.session_state.setdefault("max_loss", 5000)
    st.session_state.setdefault("last_stock_mode", None)
    st.session_state.setdefault("last_sidebar_stock", None)

    # =====================================================
    # MARKET CONTEXT SELECTION
    # =====================================================
    st.sidebar.subheader(
        "📌 Market Context Selection",
        help="Defines which symbol is analyzed. This does NOT execute trades."
    )

    stock_mode = st.sidebar.radio(
        "Symbol Selection Mode (For Analysis)",
        ["Index Based", "Manual Stock"],
        help="Index Based: Choose from predefined list.\nManual: Analyze any NSE-listed symbol."
    )

    selected_index = None
    stock = None

    # =====================================================
    # INDEX BASED MODE
    # =====================================================
    if stock_mode == "Index Based":

        selected_index = st.sidebar.selectbox(
            "Select Index",
            options=list(config.INDEX_MAP.keys()),
            help="Select the broader index universe for structured analysis."
        )

        stock_list = sorted(config.INDEX_MAP[selected_index])

        stock = st.sidebar.selectbox(
            "Select Stock",
            stock_list,
            help="Select a stock from the chosen index."
        )

    # =====================================================
    # MANUAL STOCK MODE
    # =====================================================
    else:

        manual_stock = st.sidebar.text_input(
            "Search Stock (Symbol)",
            help="Enter any NSE-listed symbol manually (e.g., RELIANCE)."
        ).upper().strip()

        stock = manual_stock if manual_stock else None

    # =====================================================
    # FINAL VALIDATION
    # =====================================================
    if not stock:
        st.sidebar.warning("Please select a stock.")
        st.stop()

    # =====================================================
    # RESET SCANNER WHEN MODE OR STOCK CHANGES
    # =====================================================
    if (
        st.session_state.last_stock_mode != stock_mode
        or st.session_state.last_sidebar_stock != stock
    ):
        st.session_state.last_stock_mode = stock_mode
        st.session_state.last_sidebar_stock = stock
        st.session_state.scanner_ready = True
        st.session_state.scanner_results = None

    st.session_state.stock = stock

    # =====================================================
    # DIRECTIONAL BIAS
    # =====================================================
    st.sidebar.markdown("### 🎯 Directional Bias (Interpretation)")
    st.sidebar.caption("ℹ️ Determines analytical bias only — not trade execution.")

    enable_short = st.sidebar.checkbox(
        "⚠️ Enable Short Bias Analysis (Advanced)",
        value=False,
        help="Enables SELL-side analytical context. Does not place short trades."
    )

    direction = st.sidebar.selectbox(
        "Select Directional Bias",
        options=["BUY", "SELL"],
        disabled=not enable_short,
        help="BUY = bullish context | SELL = bearish analytical context."
    )

    if direction == "SELL" and not enable_short:
        direction = "BUY"

    st.session_state.direction = direction

    # =====================================================
    # RISK DISCIPLINE LIMITS
    # =====================================================
    st.sidebar.markdown(
        "### 🛡 Personal Risk Discipline Limits",
        help="Personal guardrails for simulated trading discipline."
    )
    st.sidebar.caption("ℹ️ Personal discipline guardrails for paper trading only.")

    st.session_state.max_trades = st.sidebar.number_input(
        "Max Simulated Trades / Day",
        min_value=1,
        step=1,
        value=st.session_state.max_trades,
    )

    st.session_state.max_loss = st.sidebar.number_input(
        "Max Simulated Loss / Day (₹)",
        min_value=0,
        step=100,
        value=st.session_state.max_loss,
    )

    # =====================================================
    # STRATEGY LENS
    # =====================================================
    st.sidebar.markdown(
        "### 🧠 Strategy Lens (Interpretation)",
        help="Defines how market structure is interpreted."
    )
    st.sidebar.caption("ℹ️ Defines how signals are interpreted — educational only.")

    strategy = st.sidebar.radio(
        "Choose Strategy Lens",
        ["ORB Breakout", "VWAP Mean Reversion"],
    )

    st.session_state.strategy = strategy

    if strategy == "ORB Breakout":
        st.sidebar.info(
            "📈 ORB Breakout (Interpretation Lens)\n\n"
            "• First 15 minutes define range\n"
            "• Break of ORB High/Low shows momentum\n"
            "• Confirm with VWAP & volume"
        )
    else:
        st.sidebar.info(
            "📉 VWAP Mean Reversion (Interpretation Lens)\n\n"
            "• VWAP acts as institutional fair value\n"
            "• Look for pullback entries\n"
            "• Avoid strong momentum days"
        )

    # =====================================================
    # APP GUIDE
    # =====================================================
    with st.sidebar.expander("ℹ️ App Guide – How to Interpret This Tool"):
        st.markdown("""
• Sidebar settings define analysis context only  
• They do NOT place trades  
• They do NOT execute orders  
• They do NOT generate investment recommendations  
• Scanner reflects market structure only  
• All outputs are educational & analytical  
""")

    # =====================================================
    # SUBSCRIPTION CONTEXT
    # =====================================================
    user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
    tier_cfg = get_tier_config(user_tier)
    scanner_limit = tier_cfg.get("scanner_symbols")

    # =====================================================
    # REGULATORY SAFE CAPTION
    # =====================================================
    st.sidebar.markdown("---")

    st.sidebar.caption(
        "ℹ️ Sidebar settings define analysis context and discipline limits only. "
        "They do not place trades, execute orders, or provide investment advice."
    )

    if scanner_limit == 1:
        st.sidebar.caption(
            "ℹ️ Market scanner is evaluating the selected symbol only. "
            "Broader scans are available under advanced access levels."
        )

    return {
        "stock": stock,
        "direction": direction,
        "strategy": strategy,
        "user_tier": user_tier,
        "tier_cfg": tier_cfg,
        "scanner_limit": scanner_limit,
        "selected_index": selected_index,
        "stock_mode": stock_mode,  # REQUIRED for scanner gating
    }