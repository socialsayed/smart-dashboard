# =====================================================
# IMPORTS
# =====================================================
import time
import os
import streamlit as st
import pandas as pd
import config

# =====================================================
# PRODUCTION LOGGER (P3-3)
# =====================================================
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("SIDB")

SHOW_DEBUG_LOGS = False  # Toggle if deep diagnostics needed

from dashboard.layout import render_layout_header
from datetime import datetime
from dashboard.market_section import render_dashboard_header
from dashboard.sidebar import render_sidebar
from dashboard.market_section import render_market_status_and_scanner
from dashboard.price_section import render_price_section
from dashboard.chart_section import render_intraday_chart_section
from dashboard.levels_section import render_levels_section
from dashboard.sections.alerts import render_alerts_section
from dashboard.sections.trade_decision import render_trade_decision_section
from dashboard.sections.ml_advisory import render_ml_advisory_section
from dashboard.sections.paper_trade import render_paper_trade_section
from dashboard.sections.trade_analytics import render_trade_analytics_section
from utils.trade_persistence import (
    load_day_trades,
    append_trade,
    update_trade_in_csv,
    generate_trade_id,
    refresh_risk_from_history,
)
from utils.intraday_utils import (
    detect_live_support,
    detect_live_resistance,
    sanity_check_intraday,
)
from services.price_engine import (
    get_live_price_fast,
    price_freshness_label,
    poll_price,
    background_refresh,
)
from services.environment import (
    is_local_desktop,
    get_cookie_status,
)

from services.access_control import AccessControl

IS_LOCAL_DESKTOP = is_local_desktop()
cookie_status, cookie_age = get_cookie_status()

def validate_nse_symbol(symbol: str) -> bool:
    """
    Validates whether a given symbol exists on NSE
    using Yahoo Finance (.NS suffix).
    """
    if not symbol or len(symbol) < 2:
        return False

    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.fast_info
        return info is not None and "lastPrice" in info
    except Exception as e:
        logger.exception(f"validate_nse_symbol failed for {symbol}")
        if SHOW_DEBUG_LOGS:
            st.error(f"Symbol validation error: {e}")
        return False

# =====================================================
# SAFE REFRESH DEFAULT
# =====================================================
from config.subscription import (
    LIVE_REFRESH,
    DEFAULT_USER_TIER,
    get_tier_config,
)

user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
LIVE_REFRESH = LIVE_REFRESH.get(user_tier, LIVE_REFRESH["FREE"])

# --- Market & Price ---
from services.market_time import now_ist, market_status
from services.prices import live_price
import requests
from services.options import get_pcr
from services.charts import get_intraday_data

from logic.market_opportunity_scanner import run_market_opportunity_scanner

from logic.evaluate_setup import evaluate_trade_setup

# --- Data & Logic ---
from data.watchlist import daily_watchlist
from logic.levels import calc_levels


# --- Options (NIFTY) ---
from services.nifty_options import (
    get_nifty_option_chain,
    extract_atm_region,
    calculate_pcr,
    options_sentiment
)

from services.options_helpers import get_fallback_options_snapshot

# --- Utils ---
from utils.cache import init_state
from utils.charts import intraday_candlestick, add_vwap




# =====================================================
# 📘 SECTION HELP TOOLTIP TEXT
# =====================================================
SECTION_HELP = {
    "market_status": (
        "Shows whether the market is OPEN or CLOSED.\n\n"
        "What to check:\n"
        "• Is the market open?\n"
        "• Is it pre-market or post-market?\n\n"
        "Why useful:\n"
        "• Intraday trades are valid only during market hours."
    ),

    "live_price": (
        "Displays the latest traded price (LTP).\n\n"
        "What to check:\n"
        "• Is price updating?\n"
        "• Is price near support/resistance or ORB levels?\n\n"
        "Why useful:\n"
        "• All entries, exits, and risk depend on LTP."
    ),

    "intraday_chart": (
        "Shows intraday price action using candlesticks and VWAP.\n\n"
        "What to check:\n"
        "• Trend vs range\n"
        "• Strength of candles\n"
        "• Price vs VWAP\n\n"
        "Why useful:\n"
        "• Primary tool for timing trades."
    ),

    "support_resistance": (
        "Key intraday levels derived from price action.\n\n"
        "What to check:\n"
        "• Price reaction near support/resistance\n"
        "• ORB high/low tests\n\n"
        "Why useful:\n"
        "• Helps plan entries, targets, and stops."
    ),

    "alerts": (
        "Real-time alerts when important price or level events occur.\n\n"
        "What to check:\n"
        "• Breakouts\n"
        "• Breakdown\n"
        "• Level proximity\n\n"
        "Why useful:\n"
        "• Draws attention only when action matters."
    ),

    "options_pcr": (
        "Put–Call Ratio (PCR) from options data.\n\n"
        "What to check:\n"
        "• PCR > 1 → bullish bias\n"
        "• PCR < 1 → bearish bias\n\n"
        "Why useful:\n"
        "• Confirms or filters price-based trades."
    ),

    "nifty_options": (
        "ATM and nearby strike options activity.\n\n"
        "What to check:\n"
        "• PUT/CALL writing\n"
        "• OI buildup or unwinding\n\n"
        "Why useful:\n"
        "• Reveals institutional bias."
    ),

    "trade_decision": (
        "Final rule-based gate before trading.\n\n"
        "What to check:\n"
        "• Market status\n"
        "• Risk limits\n"
        "• Sentiment alignment\n\n"
        "Why useful:\n"
        "• Prevents emotional or rule-breaking trades."
    ),

    "paper_trade": (
        "Simulates trades without real money.\n\n"
        "What to check:\n"
        "• Entry price\n"
        "• Quantity\n"
        "• Live PnL\n\n"
        "Why useful:\n"
        "• Practice discipline safely."
    ),

    "trade_history": (
        "Tracks trades and PnL for the session.\n\n"
        "What to check:\n"
        "• Net PnL\n"
        "• Trade count\n\n"
        "Why useful:\n"
        "• Review performance and discipline."
    ),
}

# =====================================================
# CACHES
# =====================================================
@st.cache_data(ttl=60)
def cached_atm_analysis(df, spot):
    atm_df, atm = extract_atm_region(df, spot)
    pcr_atm = calculate_pcr(atm_df)
    ce_oi = atm_df["ce_oi_chg"].sum()
    pe_oi = atm_df["pe_oi_chg"].sum()
    return atm_df, atm, pcr_atm, ce_oi, pe_oi


@st.cache_data(ttl=30)
def cached_intraday_data(symbol):
    return get_intraday_data(symbol)


@st.cache_data(ttl=30)
def cached_index_pcr():
    return get_pcr()


@st.cache_data(ttl=60)
def cached_nifty_option_chain():
    return get_nifty_option_chain()


@st.cache_data(ttl=30)
def cached_add_vwap(df):
    """
    Cached VWAP calculation to avoid recomputation flicker.
    """
    return add_vwap(df)
    
@st.cache_data(ttl=3600)  # cache for the trading day
def cached_daily_watchlist(symbols, trade_date):
    return daily_watchlist(symbols, trade_date)
    
from concurrent.futures import ThreadPoolExecutor, as_completed

@st.cache_data(ttl=10)
def cached_watchlist_prices(symbols):

    def fetch(sym):
        try:
            p, sc = get_live_price_fast(sym)
            return {
                "Stock": sym,
                "Live Price": f"{p:.2f}" if p is not None else "—",
                "Source": sc
            }
        except Exception as e:
            logger.exception(f"Live price fetch failed for {sym}")
            if SHOW_DEBUG_LOGS:
                st.warning(f"Price fetch error for {sym}: {e}")
            return {
                "Stock": sym,
                "Live Price": "—",
                "Source": "Error"
            }

    rows = []

    # Max workers limited to avoid overload
    max_workers = min(5, len(symbols))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch, sym): sym for sym in symbols}

        for future in as_completed(futures):
            rows.append(future.result())

    # Preserve original order
    rows.sort(key=lambda x: symbols.index(x["Stock"]))

    return rows
    


# =====================================================
# 📊 INDEX PCR → STATUS + EXPLANATION + ACTION
# =====================================================
def index_pcr_status_action(pcr: float):
    if pcr is None:
        return (
            "DATA UNAVAILABLE",
            "warning",
            "Index PCR data is not available right now.",
            "Avoid index bias. Trade only with price action confirmation."
        )

    if pcr < 0.9:
        return (
            "BEARISH",
            "error",
            "Low PCR indicates heavy CALL writing. Market expects resistance or downside.",
            "Avoid BUY trades. Prefer shorts or wait for strong bullish confirmation."
        )

    if 0.9 <= pcr <= 1.1:
        return (
            "NEUTRAL / RANGE",
            "info",
            "Balanced PUT and CALL activity. No strong directional conviction.",
            "Trade only near support/resistance or VWAP. Avoid aggressive entries."
        )

    return (
        "BULLISH",
        "success",
        "High PCR shows strong PUT writing. Institutions expect the index to hold or rise.",
        "Favor BUY trades. Avoid counter-trend SELL setups."
    )

# =====================================================
# LAYOUT BOOTSTRAP (MUST BE FIRST STREAMLIT CALL)
# =====================================================
render_layout_header()

# =====================================================
# DISCLAIMER
# =====================================================
with st.expander("⚠️ IMPORTANT DISCLAIMER", expanded=False):
    st.markdown("""
### 📌 Regulatory Disclosure (SEBI)

This dashboard is a *market analytics and educational tool only*.

* It does *NOT* provide investment advice  
* It does *NOT* recommend buying or selling any security  
* It does *NOT* provide targets, stop-losses, or position sizing  
* It does *NOT* execute real trades  
* It is *NOT registered with SEBI* as an Investment Advisor  

All data, indicators, signals, and confidence scores are provided *solely for educational and analytical purposes*.

---

### 🧠 User Responsibility

Any trading decisions taken using insights from this dashboard are made *entirely at the user’s discretion and risk*.

The developer shall *not be liable* for:
* Trading losses  
* Data inaccuracies  
* Technical delays  
* Market volatility  

---

### 📘 Intended Audience

This tool is intended for:
* Learning market structure  
* Practicing discipline via paper trading  
* Understanding price, VWAP, ORB, and sentiment  

It is *NOT a substitute* for professional financial advice.
""")

# =====================================================
# SESSION STATE
# =====================================================
init_state({
    "pnl": 0.0,
    "trades": 0,
    "history": [],
    "alert_state": set(),
    "last_options_bias": None,
    "last_intraday_df": None,
    "levels": {},
    "last_price_metric": None,
    "prev_close": None,
    "last_context_key": None,
    "scanner_ready": False,
    "scanner_results": None,

    # 🔐 TIER INIT (CRITICAL FIX)
    "user_tier": DEFAULT_USER_TIER,
})

# Always sync history from disk at startup
st.session_state.history = load_day_trades()

closed = [
    t for t in st.session_state.history
    if t["Status"] == "CLOSED"
]

st.session_state.trades = len(closed)
st.session_state.pnl = sum(t["PnL"] for t in closed)

        

# =====================================================
# 📜 TABS: DASHBOARD | GUIDE | LEGAL
# =====================================================
tabs = st.tabs([
    "📊 Dashboard",
    "🧭 App Guide & How to Use",
    "📜 Legal / About"
])

# =====================================================
# 🧭 APP GUIDE & HOW TO USE
# =====================================================
with tabs[1]:
    st.markdown("## 🧭 Smart Intraday Trading — User Guide")
    
    st.markdown("""
### 🎯 What is this app?

This is a **professional intraday decision-support tool**.

It helps you:
• Read market structure  
• Observe VWAP & ORB behavior  
• Align trades with options sentiment  
• Enforce strict risk discipline  
• Practice using paper trading  

⚠️ This app **does NOT give investment advice**  
⚠️ This app **does NOT place real trades**

---

### 🔄 How refresh works (very important)

This app uses **background refresh**:

• Live price updates every 1–2 seconds  
• Charts update every ~30 seconds  
• Scanner & ML refresh silently  
• UI never resets or jumps  

👉 If the screen does not flicker, it is working correctly.

---

### 🤖 ML Setup Quality (Advisory)

ML scores setups from **0–100** based on past outcomes.

• Green → historically strong  
• Yellow → average  
• Red → weak  

ML **never overrides rules**.  
Rules always win.

---

### 📌 How to use this tool properly

• Trade only when market is OPEN  
• Wait for structure confirmation  
• Respect daily risk limits  
• Review paper trades daily  

**Discipline > Frequency**
""")

    st.info("📌 Use the first tab for live market analysis.")


# =====================================================
# 📜 LEGAL / ABOUT
# =====================================================
with tabs[2]:
    st.markdown("## 📜 Legal & Regulatory Disclosure")

    st.markdown("""
### 🔒 SEBI Status

This application is:
• NOT SEBI registered  
• NOT an advisory service  
• NOT a trading platform  

All outputs are **educational & analytical only**.

---

### ⚠️ Risk Disclosure

Trading involves substantial risk.

The developer is not responsible for:
• Trading losses  
• Missed opportunities  
• Data delays  
• System failures  

---

### 👤 User Responsibility

You are fully responsible for all trading decisions.

For advice, consult a **SEBI-registered Investment Advisor**.
""")

    st.caption("© Smart Intraday Trading — Educational Use Only")
    
# =====================================================
# 📊 DASHBOARD (ALL LIVE UI)
# =====================================================
with tabs[0]:
    import time
    t0 = time.perf_counter()
    import time
    dashboard_start = time.perf_counter()

       
    context = render_sidebar()

    
    # Re-read tier after override
    user_tier = st.session_state["user_tier"]
    tier_cfg = get_tier_config(user_tier)
    
    # --- Extract context FIRST ---
    stock = context["stock"]
    direction = context["direction"]
    strategy = context["strategy"]
    user_tier = context["user_tier"]
    tier_cfg = context["tier_cfg"]
    scanner_limit = context["scanner_limit"]
    selected_index = context["selected_index"]
    
    # -------------------------------------------------
    # ACCESS CONTROL (PHASE 4 HARD ENFORCEMENT)
    # -------------------------------------------------
    access = AccessControl()
    access.validate()
    
    # Sync validated tier back to session
    st.session_state["user_tier"] = access.user_tier
    user_tier = access.user_tier
    tier_cfg = access.tier_cfg
    
    # =====================================================
    # FREE USER INITIAL STOCK LOCK (INDEX MODE ONLY)
    # =====================================================
    
    stock_mode = context.get("stock_mode")
    
    if user_tier == "FREE" and stock_mode == "Index Based":
    
        # Store initial stock only once
        if "initial_free_stock" not in st.session_state:
            st.session_state.initial_free_stock = stock
    
    # =====================================================
    # CONTEXT CHANGE RESET (INDEX + STOCK SAFE)
    # =====================================================
    
    current_context_key = f"{context.get('stock_mode')}_{selected_index}_{stock}"
    
    if st.session_state.get("last_context_key") != current_context_key:
    
        st.session_state.last_context_key = current_context_key
    
        # Reset intraday state
        st.session_state.last_intraday_df = None
        st.session_state.last_price_metric = None
        st.session_state.prev_close = None
    
        # HARD reset scanner
        st.session_state.scanner_ready = True
        st.session_state.scanner_results = None
           
    # =====================================================
    # DASHBOARD HEADER (EXTRACTED)
    # =====================================================
    
    render_dashboard_header(user_tier)
   
    open_now, next_open = market_status()
    ist_now = now_ist()
    
    render_market_status_and_scanner(
        context={
            **context,
            "SECTION_HELP": SECTION_HELP
        },
        open_now=open_now,
        next_open=next_open,
        ist_now=ist_now,
    )
    
    st.write("⏱ Scanner time:", round(time.perf_counter() - t0, 2), "sec")
    t0 = time.perf_counter()

    # =====================================================
    # 🔄 LIVE REFRESH STATUS (SOFT-GATED BY TIER)
    # =====================================================

    # ---- Subscription context (STEP 3C) ----
    
    user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
    tier_cfg = get_tier_config(user_tier)

    # Base refresh (existing config)
    base_refresh = LIVE_REFRESH if open_now else 20

    # ---- SOFT GATE: refresh speed ----
    # Free / Basic → slower
    # Pro / Elite  → full speed
    if open_now:
        if access.can_fast_refresh:
            refresh_interval = base_refresh
        else:
            refresh_interval = max(base_refresh * 2, 15)
    else:
        refresh_interval = 20

    c1, c2 = st.columns([0.7, 0.3])

    with c1:
        st.caption(
            f"🔄 Auto-refresh every **{refresh_interval}s** "
            f"({'Market Open' if open_now else 'Market Closed'})"
        )
        
        if not tier_cfg.get("fast_refresh"):
            st.caption(
                "ℹ️ Refresh intervals may vary across access levels. "
                "Displayed data remains educational and non-advisory."
            )

    with c2:
        st.caption(
            f"🕒 Last update: {now_ist().strftime('%H:%M:%S')} IST"
        )

    poll_price(stock)
    price = st.session_state.get("last_price_metric")
    
    price_slot = st.session_state.get(f"_fast_price_{stock}")
    price_ts = price_slot.get("ts") if price_slot else None
    
    label, emoji, age = price_freshness_label(price_ts)
    
    df_intraday = st.session_state.get("last_intraday_df")
    
    open_price = high_price = low_price = None
    pct_change = range_pos = delta = None
    
    if df_intraday is not None and not df_intraday.empty and price is not None:
        open_price = df_intraday["Open"].iloc[0]
        high_price = df_intraday["High"].max()
        low_price = df_intraday["Low"].min()
    
        delta = round(price - open_price, 2)
        pct_change = round(((price - open_price) / open_price) * 100, 2)
    
        if high_price > low_price:
            range_pos = (price - low_price) / (high_price - low_price)
            
    if st.session_state.prev_close is None and price is not None:
        st.session_state.prev_close = price
    
    prev_close = st.session_state.get("prev_close")
    
    
    @st.cache_data(ttl=3600)
    def get_fundamentals(symbol: str):
        """
        Fetch fundamental data from Yahoo Finance safely.
        Cached for 1 hour.
        """
        try:
            import yfinance as yf
    
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info
    
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE")
            dividend_yield = info.get("dividendYield")
            quarterly_dividend = info.get("lastDividendValue")
    
            return {
                "market_cap": market_cap,
                "pe_ratio": pe_ratio,
                "dividend_yield": dividend_yield,
                "quarterly_dividend": quarterly_dividend,
            }
    
        except Exception as e:
            logger.exception(f"Fundamentals fetch failed for {symbol}")
            if SHOW_DEBUG_LOGS:
                st.warning(f"Fundamentals error: {e}")
    
            return {
                "market_cap": None,
                "pe_ratio": None,
                "dividend_yield": None,
                "quarterly_dividend": None,
            }
    
    fundamentals = get_fundamentals(stock)
    
    render_price_section(
        stock=stock,
        open_now=open_now,
        price=price,
        delta=delta,
        freshness_label=label,
        freshness_emoji=emoji,
        freshness_age=age,
        pct_change=pct_change,
        range_pos=range_pos,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        prev_close=prev_close,
        fundamentals=fundamentals,
    )
    
    render_intraday_chart_section(
        stock=stock,
        open_now=open_now,
        section_help=SECTION_HELP,
        cached_intraday_data=cached_intraday_data,
        cached_add_vwap=cached_add_vwap,
        sanity_check_intraday=sanity_check_intraday,
        intraday_candlestick=intraday_candlestick,
    )
    
    # =====================================================
    # WHY THIS SIGNAL?
    # =====================================================
    if strategy == "ORB Breakout":
        with st.expander("❓ Why this ORB signal?"):
            st.markdown("""
    • First 15 minutes define institutional bias  
    • Break beyond ORB shows momentum  
    • Works best with volume confirmation  
    """)
    else:
        with st.expander("❓ Why VWAP matters here?"):
            st.markdown("""
    • VWAP is institutional fair value  
    • Mean reversion works near VWAP  
    • Avoid chasing extended moves  
    """)

    st.divider()


    # =====================================================
    # EDUCATIONAL OVERLAY
    # =====================================================
    with st.expander("🎓 Beginner Help: How to Read This Dashboard"):
        st.markdown("""
    • Candlesticks show price momentum  
    • VWAP defines bias  
    • ORB shows early direction  
    • Volume confirms moves  
    • Discipline > frequency  
    """)

    st.divider()


    # =====================================================
    # DAILY WATCHLIST
    # =====================================================
    st.subheader("🎯 Daily Watchlist", help="Auto-generated focus list for the day.")

    today = now_ist().date()
    if selected_index:
        universe = config.INDEX_MAP[selected_index]
    else:
        universe = [stock]  # Manual mode → only this stock
        
    # -------------------------------------------------
    # HARD SCANNER LIMIT ENFORCEMENT (NON-BYPASSABLE)
    # -------------------------------------------------
    universe = access.enforce_scanner_limit(universe)
    
    watchlist = cached_daily_watchlist(
        universe,
        today
    )
    rows = cached_watchlist_prices(watchlist)
    st.session_state.cached_watchlist_rows = rows
    
    st.dataframe(rows, use_container_width=True)

    st.write("⏱ Watchlist time:", round(time.perf_counter() - t0, 2), "sec")
    t0 = time.perf_counter()

    st.divider()

    render_levels_section(
        price=price,
        section_help=SECTION_HELP,
        calc_levels=calc_levels,
        detect_live_support=detect_live_support,
        detect_live_resistance=detect_live_resistance,
    )

    render_alerts_section(price, SECTION_HELP)

    # =====================================================
    # INDEX OPTIONS SENTIMENT (PCR)
    # =====================================================
    st.subheader(
        "🧾 Index Options Sentiment (PCR)",
        help=SECTION_HELP["options_pcr"]
    )

    if "last_pcr_ts" not in st.session_state:
        st.session_state.last_pcr_ts = 0

    if time.time() - st.session_state.last_pcr_ts > 30:
        index_pcr = cached_index_pcr()
        st.session_state.last_pcr_ts = time.time()
    else:
        index_pcr = st.session_state.get("cached_index_pcr")

    st.session_state.cached_index_pcr = index_pcr

    status, color, explanation, action = index_pcr_status_action(index_pcr)

    # --- PCR Metric ---
    st.metric(
        "Put–Call Ratio (Index)",
        f"{index_pcr:.2f}" if index_pcr is not None else "—"
    )

    # --- Status ---
    if color == "success":
        st.success(f"🟢 Index Options Bias: {status}")
    elif color == "error":
        st.error(f"🔴 Index Options Bias: {status}")
    elif color == "warning":
        st.warning(f"⚠️ Index Options Bias: {status}")
    else:
        st.info(f"🔵 Index Options Bias: {status}")

    # --- Explanation + Action (THIS IS WHAT YOU WANTED) ---
    st.markdown("**📌 What this means:**")
    st.write(explanation)

    st.markdown("**🎯 Suggested Action:**")
    st.write(action)

    st.divider()

    # =====================================================
    # SAFE DEFAULTS (PREVENT NameError)
    # =====================================================
    # These ensure mobile / cloud users never crash the app
    atm_df = None
    df_options = None


    # =====================================================
    # NIFTY OPTIONS SENTIMENT — SAFE DEFAULT (OPTION 1)
    # =====================================================

    st.subheader("📊 NIFTY Options Sentiment")

    fallback = get_fallback_options_snapshot()

    # --- ALWAYS show fallback first ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Index", fallback["spot"])
    c2.metric("PCR", fallback["pcr"])
    c3.metric("Bias", fallback["bias"])

    st.caption(
        "📌 Data Type: Delayed / Educational\n"
        "ℹ️ Suitable for mobile, cloud, and beginners.\n"
        "ℹ️ Reflects market structure, NOT trade signals."
    )

    # --- LIVE NSE OPTIONS (TIER ENFORCED) ---
    if access.can_live_options and IS_LOCAL_DESKTOP and cookie_status == "FRESH":
    
        st.success("🖥 Desktop detected — attempting LIVE NSE options data")
    
        try:
            df_options, spot, expiry = cached_nifty_option_chain()
    
            if df_options is not None and spot is not None:
                atm_df, atm, pcr_atm, ce_oi, pe_oi = cached_atm_analysis(
                    df_options, spot
                )
                sentiment = options_sentiment(pcr_atm, ce_oi, pe_oi)
    
                st.divider()
                st.markdown("### 🔴 LIVE NSE Options (Desktop Only)")
    
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Spot", spot)
                c2.metric("ATM", atm)
                c3.metric("PCR (ATM)", round(pcr_atm, 2))
                c4.metric("Expiry", expiry)
    
                st.markdown(f"**Market Bias:** {sentiment}")
    
        except Exception as e:
            logger.exception("LIVE NSE options fetch failed")
            if SHOW_DEBUG_LOGS:
                st.error(f"NSE options error: {e}")
            st.info("ℹ️ LIVE NSE options unavailable. Showing fallback data.")
    
    elif not access.can_live_options:
        st.info(
            "🔒 Real-time NSE options data is part of advanced access levels.\n\n"
            "You are currently viewing delayed educational options sentiment.\n\n"
            "Advanced access levels include real-time options activity "
            "for deeper market structure study and intraday observation."
        )

    # =====================================================
    # USER STATUS (CLEAN, NON-SCARY)
    # =====================================================
    if IS_LOCAL_DESKTOP and cookie_status != "FRESH":
        st.info(
            "ℹ️ You are viewing delayed educational options sentiment.\n\n"
            "Real-time data may not be available in this environment."
        )


    # =====================================================
    # 📊 OI DOMINANCE (ATM ZONE)
    # =====================================================
    if atm_df is not None:
        ce_oi = atm_df["ce_oi_chg"].sum()
        pe_oi = atm_df["pe_oi_chg"].sum()

        st.caption(
            f"📊 OI Delta → CE: {ce_oi:+,.0f} | PE: {pe_oi:+,.0f}"
        )

    # =====================================================
    # 🧠 STRATEGY CONTEXT (OPTIONS-AWARE)
    # =====================================================
    options_bias = "NEUTRAL"

    if atm_df is not None:
        pcr_atm = calculate_pcr(atm_df)
        ce_oi = atm_df["ce_oi_chg"].sum()
        pe_oi = atm_df["pe_oi_chg"].sum()

        if pcr_atm is not None:
            if pcr_atm > 1.1 and pe_oi > abs(ce_oi):
                options_bias = "BULLISH"
            elif pcr_atm < 0.9 and ce_oi > abs(pe_oi):
                options_bias = "BEARISH"

    st.caption(f"🧠 Options Bias: **{options_bias}**")


    # =====================================================
    # 🔔 OPTIONS-BASED ALERTS
    # =====================================================
    options_alerts = []

    if atm_df is not None:

        # Ensure values are always defined
        pcr_atm = calculate_pcr(atm_df)
        ce_oi = atm_df["ce_oi_chg"].sum()
        pe_oi = atm_df["pe_oi_chg"].sum()

        # Strong bullish options activity
        if pcr_atm >= 1.2 and pe_oi > 100_000:
            options_alerts.append("🟢 Strong PUT Writing (Bullish Options Activity)")

        # Strong bearish options activity
        if pcr_atm <= 0.8 and ce_oi > 100_000:
            options_alerts.append("🔴 Strong CALL Writing (Bearish Options Activity)")

        # Volatility expansion
        if ce_oi > 100_000 and pe_oi > 100_000:
            options_alerts.append("⚠️ Volatility Expansion (Both CE & PE OI Rising)")

        # OI unwinding
        if ce_oi < -100_000 and pe_oi < -100_000:
            options_alerts.append("🟡 OI Unwinding (Positions Closing)")

        # Options bias flip alert
        last_bias = st.session_state.last_options_bias
        if last_bias and last_bias != options_bias:
            options_alerts.append(
                f"🔄 Options Bias Shift: {last_bias} → {options_bias}"
            )

        # Persist latest bias
        st.session_state.last_options_bias = options_bias


    # Show only NEW options alerts
    new_options_alerts = []
    for a in options_alerts:
        if a not in st.session_state.alert_state:
            new_options_alerts.append(a)
            st.session_state.alert_state.add(a)

    if new_options_alerts:
        st.subheader("🔔 Options-Based Alerts")
        for a in new_options_alerts:
            st.warning(a)

    st.caption(
        "ℹ️ This evaluation reflects **rule validation and analytical context only**. "
        "It is **not a trade call, signal, or recommendation**."
    )

    allowed, block_reason = render_trade_decision_section(
        stock=stock,
        strategy=strategy,
        price=price,
        index_pcr=index_pcr,
        options_bias=options_bias,
    )
    
    render_ml_advisory_section()
    
    paper_trade_container = st.container()

    with paper_trade_container:
        render_paper_trade_section(
            stock=stock,
            strategy=strategy,
            allowed=allowed,
            block_reason=block_reason,
            options_bias=options_bias,
            now_ist=now_ist,
            get_live_price_fast=get_live_price_fast,
            load_day_trades=load_day_trades,
            append_trade=append_trade,
            update_trade_in_csv=update_trade_in_csv,
            generate_trade_id=generate_trade_id,
            refresh_risk_from_history=refresh_risk_from_history,
        )

    st.write("⏱ Paper trade time:", round(time.perf_counter() - t0, 2), "sec")
    t0 = time.perf_counter()
    
    render_trade_analytics_section()
    