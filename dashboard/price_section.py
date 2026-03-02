import streamlit as st


# =====================================================
# LIVE PRICE SECTION (CLEAN INJECTION)
# =====================================================

def render_price_section(
    *,
    stock: str,
    open_now: bool,
    price: float | None,
    delta: float | None,
    freshness_label: str,
    freshness_emoji: str,
    freshness_age: int | None,
    pct_change: float | None,
    range_pos: float | None,
    open_price: float | None,
    high_price: float | None,
    low_price: float | None,
    prev_close: float | None,
    fundamentals: dict,
):
    """
    PURE rendering function.
    No session_state access.
    No logic computation.
    """

    # =====================================================
    # HEADER
    # =====================================================

    if open_now:
        st.markdown(
            """
            <div class="live-pulse">
                📡 Live Price
                <span class="live-dot"></span>
                <span style="color:#00c853;">LIVE</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.subheader("📡 Live Price")

    # =====================================================
    # MAIN METRIC
    # =====================================================

    st.metric(
        stock,
        f"{price:.2f}" if price is not None else "—",
        delta=f"{delta:+.2f}" if delta is not None else None,
    )

    if freshness_label:
        st.caption(
            f"{freshness_emoji} **{freshness_label}**"
            + (f" · {freshness_age}s old" if freshness_age is not None else "")
        )

    st.divider()

    # =====================================================
    # % CHANGE + DAY RANGE
    # =====================================================

    if pct_change is not None:
        color = "#2e7d32" if pct_change >= 0 else "#c62828"

        st.markdown(
            f"""
            <div style="
                font-size:0.95rem;
                color:{color};
                margin-top:-6px;
                margin-bottom:4px;
            ">
                ({pct_change:+.2f}% vs Open)
            </div>
            """,
            unsafe_allow_html=True
        )

    if range_pos is not None and open_price and high_price and low_price:
        st.progress(
            min(max(range_pos, 0.0), 1.0),
            text=(
                f"Day Range | "
                f"Low {low_price:.2f}  "
                f"Open {open_price:.2f}  "
                f"High {high_price:.2f}"
            )
        )

    st.divider()

    # =====================================================
    # SNAPSHOT
    # =====================================================

    c1, c2, c3 = st.columns(3)

    c1.metric("Open", f"{open_price:.2f}" if open_price else "—")
    c2.metric("High (Today)", f"{high_price:.2f}" if high_price else "—")
    c3.metric("Low (Today)", f"{low_price:.2f}" if low_price else "—")

    st.divider()

    # =====================================================
    # FUNDAMENTALS
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Market Cap",
        f"₹ {fundamentals.get('market_cap', 0):,} Cr"
        if fundamentals.get("market_cap") else "—"
    )

    c2.metric(
        "P/E Ratio",
        f"{fundamentals.get('pe_ratio', 0):.2f}"
        if fundamentals.get("pe_ratio") else "—"
    )

    c3.metric(
        "Dividend %",
        f"{fundamentals.get('dividend_yield', 0):.2f}%"
        if fundamentals.get("dividend_yield") else "—"
    )

    c4.metric(
        "Qtrly Dividend",
        f"₹ {fundamentals.get('quarterly_dividend', 0):.2f}"
        if fundamentals.get("quarterly_dividend") else "—"
    )

    st.divider()

    # =====================================================
    # TOP METRICS
    # =====================================================

    change = None
    pct_vs_prev = None

    if price is not None and prev_close is not None:
        change = round(price - prev_close, 2)
        pct_vs_prev = round((change / prev_close) * 100, 2)

    c1, c2, c3 = st.columns(3)

    c1.metric("LTP", price if price is not None else "—")
    c2.metric("Change", f"{change:+}" if change is not None else "—")
    c3.metric("% Change", f"{pct_vs_prev:+}%" if pct_vs_prev is not None else "—")

    st.divider()