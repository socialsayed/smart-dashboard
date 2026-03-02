import time
import streamlit as st


def render_intraday_chart_section(
    stock,
    open_now,
    section_help,
    cached_intraday_data,
    cached_add_vwap,
    sanity_check_intraday,
    intraday_candlestick,
):
    """
    Intraday chart section.
    Pure render + controlled refresh.
    No hidden state mutations outside session_state.
    """

    # -----------------------------------------
    # Controlled refresh timing (preserved)
    # -----------------------------------------
    if "last_chart_ts" not in st.session_state:
        st.session_state.last_chart_ts = 0

    if time.time() - st.session_state.last_chart_ts > 25:
        t_fetch = time.perf_counter()
        result = cached_intraday_data(stock)
        print("⏱ Intraday fetch:",
            round(time.perf_counter() - t_fetch, 3), "sec")
        st.session_state.last_chart_ts = time.time()
    else:
        result = (st.session_state.get("last_intraday_df"), None)

    if not isinstance(result, tuple) or len(result) != 2:
        df, interval = None, None
    else:
        df, interval = result

    interval_label = (
        "3-Minute" if interval == "3m"
        else "5-Minute" if interval == "5m"
        else "Intraday"
    )

    # -----------------------------------------
    # Header
    # -----------------------------------------
    if open_now:
        st.markdown(
            f"""
            <div class="live-pulse">
                📊 Intraday Chart ({interval_label})
                <span class="live-dot"></span>
                <span style="color:#00c853;">LIVE</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.subheader(
            f"📊 Intraday Chart ({interval_label})",
            help=section_help["intraday_chart"]
        )

    # -----------------------------------------
    # Sanity check + VWAP caching
    # -----------------------------------------
    if sanity_check_intraday(df, interval, stock):
    
        t_vwap = time.perf_counter()
        df = cached_add_vwap(df)
        print("⏱ VWAP calc:",
            round(time.perf_counter() - t_vwap, 3), "sec")
    
        st.session_state.last_intraday_df = df
    else:
        df = st.session_state.get("last_intraday_df")
        if df is not None:
            st.info("ℹ️ Showing last stable intraday data")

    # -----------------------------------------
    # Stable render (NO flicker)
    # -----------------------------------------
    if st.session_state.get("last_intraday_df") is None:
        st.info("⏳ Waiting for intraday data…", icon="⏳")
    else:
        t_chart = time.perf_counter()
        
        fig = intraday_candlestick(
            st.session_state.last_intraday_df,
            stock,
            interval_label
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        print("⏱ Chart render:",
            round(time.perf_counter() - t_chart, 3), "sec")