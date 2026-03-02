import streamlit as st


# =====================================================
# DASHBOARD HEADER
# =====================================================

def render_dashboard_header(user_tier: str):
    """
    Extracted Dashboard Header Block.
    Zero logic changes.
    """

    ACCESS_LABEL = user_tier.upper()

    BADGE_COLOR = {
        "FREE": "#546e7a",
        "BASIC": "#455a64",
        "PRO": "#2e7d32",
        "ELITE": "#6a1b9a",
    }.get(ACCESS_LABEL, "#455a64")

    # ---- Title + Access Badge ----
    c1, c2 = st.columns([0.75, 0.25])

    with c1:
        st.title("📊 Smart Market Analytics Dashboard")
        st.caption(
            "A professional intraday **market analytics & decision-support platform**. "
            "Provides rule-based evaluation and educational insights — **not investment advice**."
        )

    with c2:
        st.markdown(
            f"""
            <div style="text-align:right; padding-top:8px;">
                <span style="
                    display:inline-block;
                    padding:6px 14px;
                    border-radius:18px;
                    font-size:0.9rem;
                    font-weight:600;
                    color:white;
                    background:{BADGE_COLOR};
                ">
                    🪪 Access Level: {ACCESS_LABEL}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    if ACCESS_LABEL != "ELITE":
        st.caption(
            "ℹ️ Some advanced analytics are available at higher access levels. "
            "All outputs shown are educational and non-advisory."
        )

    # =====================================================
    # 🚨 IMPORTANT REGULATORY & USAGE DISCLOSURE
    # =====================================================

    st.markdown(
        """
        <div id="regulatory-box" style="
            border-left: 6px solid #455a64;
            padding: 14px 16px;
            margin: 12px 0;
            border-radius: 8px;
            font-size: 1.05rem;
            line-height: 1.5;
        ">

        <p><strong>
        ⚠️ This dashboard is for <u>market analysis and educational purposes only</u>.
        It does <span style="color:#d32f2f;">NOT provide investment advice</span>,
        does <span style="color:#d32f2f;">NOT execute real trades</span>,
        and is <span style="color:#d32f2f;">NOT registered with SEBI</span>.
        </strong></p>

        <p><strong>
        📊 A professional intraday <u>decision-support system</u> designed to help traders
        analyze <u>price structure, market sentiment, and risk</u> — <u>before taking trades</u>.
        </strong></p>

        <p><strong>
        ℹ️ Scanner results indicate <u>market conditions only</u>.
        They are <span style="color:#d32f2f;">NOT buy / sell recommendations</span>.
        </strong></p>

        <p><strong>
        ℹ️ Trade status reflects <u>rule validation only</u> and is
        <span style="color:#d32f2f;">NOT a recommendation to trade</span>.
        </strong></p>

        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# MARKET STATUS + SCANNER
# =====================================================

def render_market_status_and_scanner(
    context,
    open_now,
    next_open,
    ist_now,
):
    """
    Renders:
    - Market Status
    - Market Condition Scanner
    Pure UI extraction. No logic modified.
    """

    import config
    from logic.market_opportunity_scanner import run_market_opportunity_scanner

    stock = context["stock"]
    user_tier = context["user_tier"]
    selected_index = context["selected_index"]
    SECTION_HELP = context["SECTION_HELP"]

    # =====================================================
    # MARKET STATUS
    # =====================================================

    st.subheader(
        "🕒 Market Status",
        help=SECTION_HELP["market_status"]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("🇮🇳 IST Time", ist_now.strftime("%d %b %Y, %H:%M:%S"))
    c2.metric("Market Status", "🟢 OPEN" if open_now else "🔴 CLOSED")

    if not open_now and next_open:
        c3.metric("Next Market Open", next_open.strftime("%d %b %Y %H:%M IST"))

    st.divider()

    # =====================================================
    # MARKET CONDITION SCANNER
    # =====================================================

    st.subheader("🔎 Market Condition Scanner")

    UPGRADE_MESSAGE = (
        "ℹ️ Market Condition Scanner for manually searched symbols "
        "is available under advanced analytical access levels.\n\n"
        "This platform provides structured evaluation tools for "
        "educational purposes only and does not provide investment "
        "advice, recommendations, or trade signals."
    )

    stock_mode = context.get("stock_mode")

    # -----------------------------------------------------
    # FREE USER — MANUAL MODE → BLOCK
    # -----------------------------------------------------
    if stock_mode == "Manual Stock" and user_tier == "FREE":

        st.info(UPGRADE_MESSAGE)
        st.session_state.scanner_results = None

    # -----------------------------------------------------
    # FREE USER — INDEX MODE (INITIAL STOCK ONLY)
    # -----------------------------------------------------
    elif stock_mode == "Index Based" and user_tier == "FREE":

        initial_stock = st.session_state.get("initial_free_stock")

        if stock != initial_stock:
            st.info(UPGRADE_MESSAGE)
            st.session_state.scanner_results = None

        else:
            if st.session_state.scanner_ready:

                st.session_state.scanner_results = run_market_opportunity_scanner(
                    [stock],
                    direction=st.session_state.direction
                )

                st.session_state.scanner_ready = False

            results = st.session_state.get("scanner_results")

            if results:
                res = results[0]

                symbol = res.get("symbol", "—")
                status = res.get("status", "UNKNOWN")
                confidence = res.get("confidence", "LOW")
                reasons = res.get("reasons") or []

                message = "\n".join(f" • {r}" for r in reasons)

                if status == "BUY":
                    st.success(
                        f"🟢 Favorable Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )
                elif status == "WATCH":
                    st.warning(
                        f"🟡 Neutral / Developing Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )
                else:
                    st.error(
                        f"🔴 Unfavorable Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )

    # -----------------------------------------------------
    # BASIC / PRO / ELITE — FULL ACCESS
    # -----------------------------------------------------
    else:

        if st.session_state.scanner_ready:

            if selected_index:
                scan_symbols = list(config.INDEX_MAP[selected_index])
            else:
                scan_symbols = [stock]

            st.session_state.scanner_results = run_market_opportunity_scanner(
                scan_symbols,
                direction=st.session_state.direction
            )

            st.session_state.scanner_ready = False

        results = st.session_state.get("scanner_results")

        if not results:
            st.info("ℹ️ No symbols currently meet the defined market condition criteria.")
        else:
            for res in results:

                symbol = res.get("symbol", "—")
                status = res.get("status", "UNKNOWN")
                confidence = res.get("confidence", "LOW")
                reasons = res.get("reasons") or []

                message = "\n".join(f" • {r}" for r in reasons)

                if status == "BUY":
                    st.success(
                        f"🟢 Favorable Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )
                elif status == "WATCH":
                    st.warning(
                        f"🟡 Neutral / Developing Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )
                else:
                    st.error(
                        f"🔴 Unfavorable Conditions: {symbol} | "
                        f"Setup Quality: {confidence}\n{message}"
                    )

    st.divider()