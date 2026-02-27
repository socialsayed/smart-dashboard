# =====================================================
# IMPORTS
# =====================================================
import time
import os
import streamlit as st
import pandas as pd
import config

from datetime import datetime

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
    except Exception:
        return False

# =====================================================
# SAFE REFRESH DEFAULT
# =====================================================
LIVE_REFRESH = config.LIVE_REFRESH

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

# --- Utils ---
from utils.cache import init_state
from utils.charts import intraday_candlestick, add_vwap


# =====================================================
# 🔍 ENVIRONMENT DETECTION (LOCAL vs CLOUD / MOBILE)
# =====================================================

def is_local_desktop():
    """
    Detect if app is running locally on a desktop machine.
    Streamlit Cloud / mobile = False
    """
    return os.path.exists("data") and os.path.isdir("data")

IS_LOCAL_DESKTOP = is_local_desktop()

# =====================================================
# 🍪 NSE COOKIE STATUS & EXPIRY CHECK (AUTOMATED)
# =====================================================

COOKIE_PATH = "data/nse_cookies.json"

COOKIE_STALE_HOURS = 12      # warn user
COOKIE_EXPIRE_HOURS = 36     # force re-export


def get_cookie_age_hours():
    if not os.path.exists(COOKIE_PATH):
        return None
    mtime = os.path.getmtime(COOKIE_PATH)
    age_seconds = time.time() - mtime
    return round(age_seconds / 3600, 1)


def get_cookie_status():
    """
    Returns: (status, age_hours)

    status ∈ {"MISSING", "FRESH", "STALE", "EXPIRED"}
    """
    age = get_cookie_age_hours()

    if age is None:
        return "MISSING", None
    if age >= COOKIE_EXPIRE_HOURS:
        return "EXPIRED", age
    if age >= COOKIE_STALE_HOURS:
        return "STALE", age
    return "FRESH", age

# =====================================================
# 🍪 NSE COOKIE STATUS (INITIALIZE ONCE)
# =====================================================
# This MUST be initialized once and reused everywhere
cookie_status, cookie_age = get_cookie_status()


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

def detect_live_support(df: pd.DataFrame, lookback=3):
    """
    Detects nearest live support based on swing lows.
    Returns price level or None.
    """
    if df is None or len(df) < lookback * 2 + 1:
        return None

    lows = df["Low"].values
    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        if (
            lows[i] < min(lows[i - lookback:i]) and
            lows[i] < min(lows[i + 1:i + lookback + 1])
        ):
            swing_lows.append(lows[i])

    if not swing_lows:
        return None

    current_price = df["Close"].iloc[-1]
    valid = [l for l in swing_lows if l < current_price]

    return max(valid) if valid else None


def detect_live_resistance(df: pd.DataFrame, lookback=3):
    """
    Detects nearest live resistance based on swing highs.
    Returns price level or None.
    """
    if df is None or len(df) < lookback * 2 + 1:
        return None

    highs = df["High"].values
    swing_highs = []

    for i in range(lookback, len(df) - lookback):
        if (
            highs[i] > max(highs[i - lookback:i]) and
            highs[i] > max(highs[i + 1:i + lookback + 1])
        ):
            swing_highs.append(highs[i])

    if not swing_highs:
        return None

    current_price = df["Close"].iloc[-1]
    valid = [h for h in swing_highs if h > current_price]

    return min(valid) if valid else None
    
def refresh_risk_from_history():
    closed = [
        t for t in st.session_state.history
        if t["Status"] == "CLOSED" and isinstance(t.get("PnL"), (int, float))
    ]
    st.session_state.trades = len(closed)
    st.session_state.pnl = sum(t["PnL"] for t in closed)
    
   

    
# =====================================================
# 📊 FALLBACK OPTIONS DATA (MOBILE / CLOUD SAFE)
# =====================================================

def get_fallback_options_snapshot():
    """
    Delayed / indicative options sentiment
    SAFE for mobile & cloud users
    """
    return {
        "spot": "NIFTY 50",
        "pcr": 1.02,
        "bias": "NEUTRAL",
        "oi_summary": "Balanced PUT & CALL activity",
        "data_type": "Delayed / Indicative",
    }

# =====================================================
# 🔍 SANITY CHECK (INTRADAY DATA)
# FIXED: interval=None treated as cached / unchanged
# SIDB v2.4.1 SAFE
# =====================================================
def sanity_check_intraday(df, interval, symbol):
    # --- Basic availability ---
    if df is None or df.empty:
        st.warning(f"⚠️ {symbol}: Intraday data unavailable")
        return False

    # --- Required columns ---
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        st.warning(f"⚠️ Missing OHLC columns: {missing}")
        return False

    # --- Time ordering ---
    if not hasattr(df.index, "is_monotonic_increasing") or not df.index.is_monotonic_increasing:
        st.warning("⚠️ Intraday candles not time-sorted")

    # --- NaN density ---
    if df[list(required)].isna().mean().mean() > 0.25:
        st.warning("⚠️ High NaN density in intraday candles")

    # --- Live candle completeness ---
    if df.iloc[-1][list(required)].isna().any():
        st.warning("⚠️ Latest candle incomplete (live candle)")

    # --- Interval validation ---
    # IMPORTANT:
    # interval = None is VALID in SIDB (cached / unchanged interval)
    if interval is not None:
        allowed_intervals = {"1m", "2m", "3m", "5m", "15m", "30m", "60m"}
        if interval not in allowed_intervals:
            st.warning(f"⚠️ Unsupported interval: {interval}")

    return True

# =====================================================
# 📁 PAPER TRADE PERSISTENCE (DAILY)
# =====================================================

PAPER_TRADE_DIR = "data/paper_trades"

def get_trade_date():
    return now_ist().date().isoformat()

def get_trade_file():
    os.makedirs(PAPER_TRADE_DIR, exist_ok=True)
    return os.path.join(PAPER_TRADE_DIR, f"{get_trade_date()}.csv")

def load_day_trades():
    path = get_trade_file()

    if not os.path.exists(path):
        return []

    try:
        # Use python engine for schema tolerance
        df = pd.read_csv(
    path,
    engine="python",
    on_bad_lines="skip"
)
    except Exception as e:
        st.error(f"⚠️ Paper trade CSV corrupted: {e}")
        return []

    # 🔒 Enforce fixed schema
    expected_cols = [
        "Trade ID",
        "Date",
        "Symbol",
    
        # 🔒 Direction of trade (LOCKED)
        # BUY  = Long
        # SELL = Short
        "Side",
    
        "Entry",
        "Exit",
        "Qty",
        "PnL",
        "Entry Time",
        "Exit Time",
        "Strategy",
        "Options Bias",
        "Market Status",
        "Notes",
        "Status",
    ]

    # Add missing columns safely
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Drop extra columns silently
    df = df[expected_cols]

    return df.to_dict("records")


def append_trade(row: dict):
    path = get_trade_file()
    df = pd.DataFrame([row])
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", header=header, index=False)
    
def update_trade_in_csv(trade_id: str, updates: dict):
    path = get_trade_file()
    if not os.path.exists(path):
        return

    df = pd.read_csv(path)

    if "Trade ID" not in df.columns:
        return

    mask = df["Trade ID"] == trade_id
    if not mask.any():
        return

    for k, v in updates.items():
        if k in df.columns:
            df.loc[mask, k] = v

    df.to_csv(path, index=False)
    
    
def generate_trade_id():
    return f"T{int(time.time() * 1000)}"
    
    

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
    
# =====================================================
# ⚡ FAST LIVE PRICE ENGINE (PER-SYMBOL, NON-BLOCKING)
# =====================================================
def get_live_price_fast(symbol, min_interval=1.5):
    """
    Fetch live price via shared data service.
    Tracks server timestamp for freshness labeling.
    """

    key = f"_fast_price_{symbol}"

    if key not in st.session_state:
        st.session_state[key] = {
            "ts": None,          # server timestamp
            "poll_ts": 0,        # local poll throttle
            "price": None,
            "src": None,
        }

    slot = st.session_state[key]
    now = time.time()

    if now - slot["poll_ts"] >= min_interval:
        try:
            resp = requests.get(
                f"http://127.0.0.1:8000/price/{symbol}",
                timeout=0.8
            )

            if resp.status_code == 200:
                data = resp.json()
                slot["price"] = data.get("price")
                slot["src"] = "SHARED_LIVE"

                # ✅ server timestamp (UTC ISO)
                ts = data.get("timestamp")
                if ts:
                    slot["ts"] = datetime.fromisoformat(ts).timestamp()

            else:
                raise RuntimeError("Shared service error")

        except Exception:
            # Fallback
            try:
                slot["price"], slot["src"] = live_price(symbol)
                slot["ts"] = time.time()
            except Exception:
                pass

        slot["poll_ts"] = now

    return slot["price"], slot["src"]
    
# =====================================================
# 🔁 PRICE POLLING (NO RERUN, NO UI RESET)
# =====================================================
def price_freshness_label(price_ts):
    """
    Returns (label, emoji, age_seconds)
    """
    if not price_ts:
        return "DELAYED", "🔴", None

    age = time.time() - price_ts

    if age <= 3:
        return "LIVE", "🟢", int(age)
    if age <= 15:
        return "NEAR-LIVE", "🟡", int(age)
    return "DELAYED", "🔴", int(age)
    
def poll_price(symbol):
    """
    Poll live price safely and update session_state.
    This function is REQUIRED because the UI calls it.
    """

    price, src = get_live_price_fast(symbol)

    if price is not None:
        st.session_state.last_price_metric = price

    return price, src    

# =====================================================
# 🔁 BACKGROUND DATA REFRESH (NON-DISRUPTIVE)
# =====================================================
def background_refresh(symbol, open_now):
    """
    Refresh heavy data WITHOUT touching UI.
    Safe: updates session_state only.
    """

    now = time.time()

    # ---- Intraday data (slow, chart-related) ----
    if now - st.session_state.get("last_intraday_refresh", 0) > 30:
        try:
            df, interval = cached_intraday_data(symbol)
            if df is not None and not df.empty:
                df = cached_add_vwap(df)
                st.session_state.last_intraday_df = df
        except Exception:
            pass

        st.session_state.last_intraday_refresh = now

    # ---- Index PCR (slow) ----
    if now - st.session_state.get("last_pcr_refresh", 0) > 30:
        try:
            st.session_state.cached_index_pcr = cached_index_pcr()
        except Exception:
            pass

        st.session_state.last_pcr_refresh = now

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
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Smart Market Analytics — Intraday Decision Support",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* ===============================
       SAFE HEADER STYLING (DO NOT REMOVE HEADER)
       =============================== */

    header[data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;
    }

    /* Reduce header height, don't kill it */
    header[data-testid="stHeader"] {
        height: auto !important;
    }

    /* Main content spacing */
    [data-testid="stMainBlockContainer"] {
        padding-top: 0.5rem !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ---------- make `st.info` boxes readable in light & dark themes (and regulatory box) ----------
st.markdown(
    """
    <style>
    /* style alerts for contrast */
    @media (prefers-color-scheme: dark) {
        .stAlert, .stAlertInfo, .stAlert *, .stAlertInfo *, #regulatory-box {
            color: #fff !important;
            background-color: #333 !important;
        }
    }
    @media (prefers-color-scheme: light) {
        .stAlert, .stAlertInfo, .stAlert *, .stAlertInfo *, #regulatory-box {
            color: #000 !important;
            background-color: #eee !important;
        }
    }
    /* ensure container also inherits */
    .stAlert, .stAlertInfo, #regulatory-box {
        color: inherit !important;
        background-color: inherit !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
    "last_stock": None,
    "scanner_ready": False,   # ✅ ADD THIS
})

# Load persisted trades for today (OPEN + CLOSED)
if not st.session_state.history:
    st.session_state.history = load_day_trades()

    closed = [t for t in st.session_state.history if t["Status"] == "CLOSED"]
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
    # =====================================================
    # HEADER
    # =====================================================
    st.title("📊 Smart Market Analytics Dashboard")
    
    st.caption(
        "A professional intraday **market analytics & decision-support platform**. "
        "Provides rule-based evaluation and educational insights — **not investment advice**."
    )

    # =====================================================
    # 🚨 IMPORTANT REGULATORY & USAGE DISCLOSURE (PROMINENT)
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
    # SESSION DEFAULTS (SAFE, REQUIRED)
    # =====================================================
    st.session_state.setdefault("index", list(config.INDEX_MAP.keys())[0])
    st.session_state.setdefault(
        "stock",
        config.INDEX_MAP[st.session_state.index][0]
    )
    st.session_state.setdefault("strategy", "ORB Breakout")
    st.session_state.setdefault("max_trades", 1000)
    st.session_state.setdefault("max_loss", 5000)

    # =====================================================
    # 📌 MARKET SELECTION (INPUT ONLY)
    # =====================================================
    
    st.sidebar.subheader("📌 Market Context Selection")
    
    stock_mode = st.sidebar.radio(
        "Symbol Selection Mode (For Analysis)",
        ["Index Based", "Manual Stock"],
        help="Choose stocks from index or manually search any NSE stock"
    )
    
    selected_index = st.sidebar.selectbox(
        "Select Index",
        options=list(config.INDEX_MAP.keys()),
    )
    
    selected_stock = None
    manual_stock = None
    
    if stock_mode == "Index Based":
        stock_list = sorted(config.INDEX_MAP[selected_index])
        selected_stock = st.sidebar.selectbox(
            "Select Stock",
            stock_list,
        )
    
    if stock_mode == "Manual Stock":
        manual_stock = st.sidebar.text_input(
            "Search Stock (Symbol or Name)",
            placeholder="e.g. RELIANCE, TCS, INFY (Analysis only)",
        ).upper().strip()
        
        manual_symbol = manual_stock   # ← THIS is “immediately after”
            
    # =====================================================
    # 🎯 FINAL ACTIVE STOCK RESOLUTION (SINGLE SOURCE OF TRUTH)
    # =====================================================
    
    stock = None  # ✅ THIS VARIABLE MUST EXIST
    
    if stock_mode == "Manual Stock":
        if manual_stock:
            if validate_nse_symbol(manual_stock):
                stock = manual_stock
                st.sidebar.success(f"✅ NSE Stock Found: {manual_stock}")
            else:
                st.sidebar.error(f"❌ Invalid NSE Symbol: {manual_stock}")
                st.stop()
        else:
            st.sidebar.warning("Please enter a stock symbol")
            st.stop()
    
    else:  # Index Based
        if selected_stock:
            stock = selected_stock
        else:
            st.sidebar.warning("Please select a stock")
            st.stop()
    
    # 🔒 Persist & detect change
    if st.session_state.get("last_stock") != stock:
        st.session_state.last_stock = stock
        st.session_state.last_intraday_df = None
        st.session_state.last_price_metric = None
        st.session_state.scanner_ready = True   # ✅ KEY LINE
    
    st.session_state.stock = stock
    
    # =====================================================
    # 🎯 TRADE DIRECTION SELECTION
    # =====================================================
    
    st.sidebar.markdown("### 🎯 Directional Bias (Interpretation)")
    
    # Safety guardrail for shorts
    enable_short = st.sidebar.checkbox(
        "⚠️ Enable Short Bias Analysis (Advanced)",
        value=False,
        help="Short selling is advanced and risky. Enable only if you fully understand short trade mechanics."
    )
    
    direction = st.sidebar.selectbox(
        "Select Directional Bias",
        options=["BUY", "SELL"],
        index=0,
        disabled=not enable_short,
    )
    
    # Absolute safety fallback
    if direction == "SELL" and not enable_short:
        direction = "BUY"
    
    # Persist direction
    st.session_state.direction = direction
    
    # =====================================================
    # SIDEBAR – RISK LIMITS
    # =====================================================
    st.sidebar.header(
        "🛡 Personal Risk Discipline Limits",
        help="Daily risk controls to enforce discipline."
    )

    max_trades = st.sidebar.number_input(
        "Max Simulated Trades / Day",
        min_value=1,
        max_value=1000,
        value=st.session_state.max_trades,
        key="max_trades"
    )

    max_loss = st.sidebar.number_input(
        "Max Simulated Loss / Day (₹)",
        min_value=1000,
        max_value=500000,
        value=st.session_state.max_loss,
        key="max_loss"
    )

    # =====================================================
    # SIDEBAR – STRATEGY MODE
    # =====================================================
    st.sidebar.header(
        "🧠 Strategy Lens (Interpretation)",
        help="Choose the strategy lens for interpretation."
    )

    strategy = st.sidebar.radio(
        "Choose Strategy Lens",
        ["ORB Breakout", "VWAP Mean Reversion"],
        key="strategy"
    )

    if strategy == "ORB Breakout":
        st.sidebar.info(
            "📈 **ORB Breakout (Interpretation Lens)**\n\n"
            "• First 15 minutes define range\n"
            "• Trade break of ORB High / Low\n"
            "• Works best on trending days\n"
            "• Confirm with volume & VWAP"
        )
    else:
        st.sidebar.info(
            "📉 **VWAP Mean Reversion (Interpretation Lens)**\n\n"
            "• VWAP = institutional fair price\n"
            "• Trade pullbacks & rejections\n"
            "• Best on balanced / sideways days"
        )

    # =====================================================
    # ⬇️ ALL YOUR EXISTING DASHBOARD CODE CONTINUES HERE
    # (Market status, charts, scanner, trades, etc.)
    # =====================================================

    # =====================================================
    # ℹ️ SIDEBAR – APP GUIDE / HOW TO USE
    # =====================================================
    with st.sidebar.expander("ℹ️ App Guide – How to Interpret This Tool", expanded=False):
    
        st.markdown("""
    ### 🎯 What is this app?
    This is a **Smart Intraday Trading tool** designed to help traders make
    **disciplined, rule-based decisions** using:
    
    • Price action  
    • VWAP & ORB structure  
    • Options sentiment (PCR & OI)  
    • Risk management rules  
    
    ⚠️ This app **does NOT place real trades** and **does NOT give investment advice**.
    It is a **decision-support and learning tool**.
    
    ---
    ### 🕒 Market & Time Awareness
    **What it does**
    • Shows IST time  
    • Detects market OPEN / CLOSED  
    • Displays countdown to next session  
    
    **What to check**
    • Take intraday trades only when market is OPEN  
    • Use pre-market only for bias, not entries  
    
    ---
    ### 📡 Live Price Engine
    **What it does**
    • Fetches live LTP  
    • Uses caching to prevent flicker  
    
    **What to check**
    • Is price updating smoothly?  
    • Is price near support, resistance, ORB, or VWAP?  
    
    ---
    ### 📊 Intraday Chart + Sanity Checks
    **What it does**
    • Displays intraday candlesticks  
    • Adds VWAP  
    • Runs automatic data sanity checks  
    
    **Sanity checks include**
    • Missing candles  
    • Out-of-order timestamps  
    • Excessive NaN values  
    • Incomplete live candle  
    
    **How to use**
    • Trust signals only when data is clean  
    • If fallback data is shown, be cautious  
    
    ---
    ### 📌 Support, Resistance & ORB Levels
    **What it does**
    • Calculates dynamic intraday levels  
    • Identifies ORB High & Low  
    
    **What to check**
    • Reaction at levels (acceptance vs rejection)  
    • Avoid first-touch trades  
    • Wait for confirmation  
    
    ---
    ### 🔔 Alerts System
    **What it does**
    • Generates alerts only on **new events**  
    • Prevents repeated noise  
    
    **How to use**
    • Alerts draw attention — they are NOT trade commands  
    • Always confirm using chart & context  
    
    ---
    ### 🧾 Options Sentiment (PCR & OI)
    **What it does**
    • Computes Put–Call Ratio (PCR)  
    • Analyzes ATM option OI changes  
    • Detects bullish / bearish bias  
    
    **What to check**
    • PCR > 1 → bullish context  
    • PCR < 1 → bearish context  
    • Align options bias with price action  
    
    ---
    ### 📈 Trade Decision Engine
    **What it does**
    • Combines:
    – Market status  
    – Risk limits  
    – Price structure  
    – Options bias  
    
    **Important**
    • Trade ALLOWED ≠ Trade REQUIRED  
    • Trade BLOCKED = stand aside  
    
    ---
    ### 🧪 Paper Trade Simulator
    **What it does**
    • Simulates trades without real money  
    • Saves trades for the entire trading day  
    • Auto-resets on next day  
    
    **What to check**
    • Entry discipline  
    • Exit discipline  
    • Emotional control  
    
    ---
    ### 📒 Trade History & Review
    **What it does**
    • Tracks trades & PnL  
    • Enables self-review  
    
    **What to analyze**
    • Overtrading  
    • Strategy effectiveness  
    • Consistency vs impulse  
    
    ---
    ### 🧠 Final Reminder
    This dashboard is designed to **protect you from bad trades**,  
    not to increase trade frequency.
    
    Discipline > Frequency  
    Process > Outcome
    """)
    
    st.sidebar.caption(
        "ℹ️ Sidebar settings define **analysis context and personal discipline limits only**. "
        "They do **not** place trades, execute orders, or generate investment recommendations."
    )
    
    # =====================================================
    # 🔧 SCANNER SYMBOL SELECTION (FIXED – READ ONLY)
    # =====================================================

    # Single source of truth for scanner symbols
    scan_symbols = [st.session_state.stock]

    # Gentle reminder for manual scans
    st.sidebar.caption(
        "ℹ️ Manual symbol scanning is enabled, but results may not be "
        "accurate for names not in the index map."
    )

    # =====================================================
    # MARKET STATUS
    # =====================================================
    st.subheader(
        "🕒 Market Status",
        help=SECTION_HELP["market_status"]
    )

    open_now, next_open = market_status()
    ist_now = now_ist()

    c1, c2, c3 = st.columns(3)

    c1.metric("🇮🇳 IST Time", ist_now.strftime("%d %b %Y, %H:%M:%S"))
    c2.metric("Market Status", "🟢 OPEN" if open_now else "🔴 CLOSED")

    if not open_now and next_open:
        c3.metric("Next Market Open", next_open.strftime("%d %b %Y %H:%M IST"))

    st.divider()


    if "alert_state" not in st.session_state:
        st.session_state.alert_state = set()

        # =====================================================
        # 🔎 MARKET OPPORTUNITY SCANNER OUTPUT (SOFT-GATED)
        # =====================================================
    
        # ---- Subscription context (STEP 3B) ----
        from config.subscription import (
            DEFAULT_USER_TIER,
            get_tier_config,
        )
    
        # Current user tier (no auth yet)
        user_tier = st.session_state.get("user_tier", DEFAULT_USER_TIER)
        tier_cfg = get_tier_config(user_tier)
    
        scanner_limit = tier_cfg.get("scanner_max_symbols")
        scanner_refresh_seconds = tier_cfg.get("scanner_refresh_seconds", 30)
    
        if open_now and st.session_state.scanner_ready:
            st.subheader("🔎 Market Condition Scanner")
    
            st.caption(
                "ℹ️ The Market Condition Scanner highlights **market conditions only**. "
                "Results are analytical and educational — **not trade signals or advice**."
            )
    
            scanner_results = run_market_opportunity_scanner(
                scan_symbols,
                direction=st.session_state.direction
            )
    
            st.session_state.scanner_ready = False
    
            # ---- SOFT GATE: limit visible results ----
            if scanner_limit is not None:
                visible_results = scanner_results[:scanner_limit]
            else:
                visible_results = scanner_results
    
            if not visible_results:
                st.info(
                    "ℹ️ No symbols currently meet the defined market condition criteria. "
                    "This does not imply a trading opportunity or restriction."
                )
            else:
                for res in visible_results:
    
                    symbol = res.get("symbol", "—")
                    status = res.get("status", "UNKNOWN")
                    confidence = res.get("confidence", "LOW")
    
                    reasons = res.get("reasons") or [
                        "No detailed rationale available (scanner context only)"
                    ]
    
                    ml_badge = ""
                    if (
                        tier_cfg.get("show_ml_score_numeric")
                        and "ml_score" in res
                        and res["ml_score"] is not None
                    ):
                        ml_badge = f" | 🤖 ML: {int(res['ml_score'] * 100)}"
    
                    if status == "BUY":
                        st.success(
                            f"🟢 Favorable Conditions: {symbol} | "
                            f"Setup Quality: {confidence}{ml_badge}\n"
                            + "\n".join(f" • {r}" for r in reasons)
                        )
                    elif status == "WATCH":
                        st.warning(
                            f"🟡 Developing Conditions: {symbol} | "
                            f"Setup Quality: {confidence}{ml_badge}\n"
                            + "\n".join(f" • {r}" for r in reasons)
                        )
                    else:
                        st.error(
                            f"🔴 Unfavorable Conditions: {symbol} | "
                            f"Setup Quality: {confidence}{ml_badge}\n"
                            + "\n".join(f" • {r}" for r in reasons)
                        )
    
            # ---- Tier visibility note (non-intrusive) ----
            if scanner_limit is not None and len(scanner_results) > scanner_limit:
                st.caption(
                    f"ℹ️ Showing top {scanner_limit} results for **{user_tier}** tier. "
                    "Additional symbols are hidden to reduce noise."
                )
    
            st.caption(
                "ℹ️ Scanner classifications reflect **market context only**. "
                "They are **not trade calls or recommendations**."
            )


    # =====================================================
    # 🔄 LIVE REFRESH STATUS
    # =====================================================
    refresh_interval = LIVE_REFRESH if open_now else 20

    c1, c2 = st.columns([0.7, 0.3])

    with c1:
        st.caption(
            f"🔄 Auto-refresh every **{refresh_interval}s** "
            f"({'Market Open' if open_now else 'Market Closed'})"
        )

    with c2:
        st.caption(
            f"🕒 Last update: {now_ist().strftime('%H:%M:%S')} IST"
        )

    # 🔁 Silent background refresh (NO UI impact)
    background_refresh(stock, open_now)

    # =====================================================
    # LIVE PRICE (TERMINAL-GRADE)
    # =====================================================
    # Live Price header (LIVE only when market is OPEN)
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
        st.subheader(
            "📡 Live Price",
            help=SECTION_HELP["live_price"]
        )

    poll_price(stock)
    price = st.session_state.get("last_price_metric")

    price_slot = st.session_state.get(f"_fast_price_{stock}")
    price_ts = price_slot.get("ts") if price_slot else None
    

    # Initialize previous close ONCE
    if st.session_state.prev_close is None and price is not None:
        st.session_state.prev_close = price

    # Delta vs TODAY OPEN (terminal-grade, correct)
    delta = None
    open_price = None

    df_intraday = st.session_state.get("last_intraday_df")

    # Prefer true intraday OPEN
    if df_intraday is not None and not df_intraday.empty:
        open_price = df_intraday["Open"].iloc[0]

    # Fallback ONLY if intraday data not ready yet
    elif st.session_state.prev_close is not None:
        open_price = st.session_state.prev_close

    if price is not None and open_price is not None:
        delta = round(price - open_price, 2)

    price_slot = st.session_state.get(f"_fast_price_{stock}")
    price_ts = price_slot.get("ts") if price_slot else None
    
    label, emoji, age = price_freshness_label(price_ts)
    
    st.metric(
        stock,
        f"{price:.2f}" if price is not None else "—",
        delta=f"{delta:+.2f}" if delta is not None else None,
    )
    
    # ✅ VISIBLE freshness badge
    if label:
        st.caption(
            f"{emoji} **{label}**"
            + (f" · {age}s old" if age is not None else "")
        )

    # 🔥 UPDATE LAST PRICE AFTER UI RENDER
    if price is not None:
        st.session_state.last_price_metric = price
    else:
        st.warning(
            "⚠️ Unable to fetch live price for the selected symbol. "
            "The ticker may be invalid, delisted, or data source is down."
        )

    st.divider()

    # if the intraday dataframe is empty later we will show a separate
    # warning further down; clearing here ensures we notice it quickly

    # =====================================================
    # 📈 LIVE PRICE CONTEXT — % vs OPEN + DAY RANGE BAR
    # =====================================================

    df_intraday = st.session_state.get("last_intraday_df")

    open_price = high_price = low_price = None
    pct_change = None
    range_pos = None

    if df_intraday is not None and not df_intraday.empty and price is not None:
        open_price = df_intraday["Open"].iloc[0]
        high_price = df_intraday["High"].max()
        low_price = df_intraday["Low"].min()

        # % change vs OPEN
        pct_change = round(((price - open_price) / open_price) * 100, 2)

        # Day range position (0 → 1)
        if high_price > low_price:
            range_pos = (price - low_price) / (high_price - low_price)
    else:
        # no intraday data available for this stock
        st.warning(
            "⚠️ Intraday candles temporarily unavailable from data source. "
            "Live price is valid. Charts & ORB/VWAP are paused for safety."
        )

    # ---------- Color intensity based on distance from OPEN ----------
    delta_color = "#888888"  # neutral fallback

    if open_price is not None and price is not None:
        distance = abs(price - open_price) / open_price

        if price >= open_price:
            delta_color = (
                "#1b5e20" if distance > 0.015 else   # strong green
                "#2e7d32" if distance > 0.008 else   # medium green
                "#66bb6a"                            # light green
            )
        else:
            delta_color = (
                "#b71c1c" if distance > 0.015 else   # strong red
                "#c62828" if distance > 0.008 else   # medium red
                "#ef5350"                            # light red
            )

    # ---------- % CHANGE DISPLAY (UNDER DELTA) ----------
    if pct_change is not None:
        st.markdown(
            f"""
            <div style="
                font-size:0.95rem;
                color:{delta_color};
                margin-top:-6px;
                margin-bottom:4px;
            ">
                ({pct_change:+.2f}% vs Open)
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------- DAY RANGE PROGRESS BAR ----------
    if range_pos is not None:
        st.progress(
            min(max(range_pos, 0.0), 1.0),
            text=(
                f"Day Range | "
                f"Low {low_price:.2f}  "
                f"Open {open_price:.2f}  "
                f"High {high_price:.2f}"
            )
        )

    # =====================================================
    # 📌 LIVE SNAPSHOT — TODAY RANGE + FUNDAMENTALS
    # =====================================================

    # ---------- TODAY OPEN / HIGH / LOW (from intraday data) ----------
    today_open = today_high = today_low = None

    df_intraday = st.session_state.get("last_intraday_df")

    if df_intraday is not None and not df_intraday.empty:
        today_open = df_intraday["Open"].iloc[0]
        today_high = df_intraday["High"].max()
        today_low = df_intraday["Low"].min()

    c1, c2, c3 = st.columns(3)

    c1.metric("Open", f"{today_open:.2f}" if today_open else "—")
    c2.metric("High (Today)", f"{today_high:.2f}" if today_high else "—")
    c3.metric("Low (Today)", f"{today_low:.2f}" if today_low else "—")

    st.divider()

    # ---------- FUNDAMENTALS (SLOW-CHANGING, SAFE) ----------
    # NOTE:
    # Replace the placeholder fetch below with your preferred source
    # (Yahoo Finance, NSE, Screener API, etc.)

    @st.cache_data(ttl=3600)
    def get_fundamentals(symbol):
        """
        Expected return dict keys:
        market_cap, pe_ratio, dividend_yield, quarterly_dividend
        """
        return {
            "market_cap": None,
            "pe_ratio": None,
            "dividend_yield": None,
            "quarterly_dividend": None,
        }

    fundamentals = get_fundamentals(stock)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Market Cap",
        f"₹ {fundamentals['market_cap']:,} Cr"
        if fundamentals["market_cap"] else "—"
    )

    c2.metric(
        "P/E Ratio",
        f"{fundamentals['pe_ratio']:.2f}"
        if fundamentals["pe_ratio"] else "—"
    )

    c3.metric(
        "Dividend %",
        f"{fundamentals['dividend_yield']:.2f}%"
        if fundamentals["dividend_yield"] else "—"
    )

    c4.metric(
        "Qtrly Dividend",
        f"₹ {fundamentals['quarterly_dividend']:.2f}"
        if fundamentals["quarterly_dividend"] else "—"
    )

    # =====================================================
    # TOP METRICS
    # =====================================================
    st.subheader("📊 Top Metrics")

    ltp = st.session_state.get("last_price_metric")
    prev_close = st.session_state.get("prev_close")

    change = pct_change = None
    if ltp is not None and prev_close is not None:
        change = round(ltp - prev_close, 2)
        pct_change = round((change / prev_close) * 100, 2)

    c1, c2, c3 = st.columns(3)

    c1.metric("LTP", ltp if ltp is not None else "—")
    c2.metric("Change", f"{change:+}" if change is not None else "—")
    c3.metric("% Change", f"{pct_change:+}%" if pct_change is not None else "—")

    st.divider()


    # =====================================================
    # INTRADAY CHART
    # =====================================================

    if "last_chart_ts" not in st.session_state:
        st.session_state.last_chart_ts = 0

    if time.time() - st.session_state.last_chart_ts > 25:
        result = cached_intraday_data(stock)
        st.session_state.last_chart_ts = time.time()
    else:
        result = (st.session_state.last_intraday_df, None)

    if not isinstance(result, tuple) or len(result) != 2:
        df, interval = None, None
    else:
        df, interval = result

    interval_label = (
        "3-Minute" if interval == "3m"
        else "5-Minute" if interval == "5m"
        else "Intraday"
    )

    # Intraday Chart header (LIVE only when market is OPEN)
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
            help=SECTION_HELP["intraday_chart"]
        )

    if sanity_check_intraday(df, interval, stock):
        df = cached_add_vwap(df)
        st.session_state.last_intraday_df = df
    else:
        df = st.session_state.last_intraday_df
        if df is not None:
            st.info("ℹ️ Showing last stable intraday data")

    # ============================================================
    # SIDB v2.4.1 — Stable Intraday Chart Render (NO FLICKER)
    # ============================================================

    # Case 1: First-ever load → show placeholder
    if st.session_state.last_intraday_df is None:
        st.info("⏳ Waiting for intraday data…", icon="⏳")

    # Case 2: We have a stable chart → ALWAYS show it
    else:
        fig = intraday_candlestick(
            st.session_state.last_intraday_df,
            stock,
            interval_label
        )
        st.plotly_chart(fig, use_container_width=True)

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
    watchlist = cached_daily_watchlist(
        config.INDEX_MAP[selected_index],
        today
    )
    rows = []
    for sym in watchlist:
        p, sc = get_live_price_fast(sym)

        rows.append({
            "Stock": sym,
            "Live Price": f"{p:.2f}" if p is not None else "—",
            "Source": sc
        })

    st.dataframe(rows, use_container_width=True)

    st.divider()


    # =====================================================
    # SUPPORT & RESISTANCE + LIVE CONTEXT
    # =====================================================
    st.subheader(
        "📌 Live Support & Resistance",
        help=SECTION_HELP["support_resistance"]
    )

    # --- Ensure levels are always defined FIRST ---
    levels = st.session_state.get("levels", {})

    last_price = st.session_state.get("last_price")

    if price and price != last_price:
        levels = calc_levels(price)
        st.session_state.levels = levels
        st.session_state.last_price = price

    # --- Live support / resistance from intraday structure ---
    live_support = None
    live_resistance = None

    if st.session_state.last_intraday_df is not None:
        live_support = detect_live_support(
            st.session_state.last_intraday_df
        )
        live_resistance = detect_live_resistance(
            st.session_state.last_intraday_df
        )

    # --- Metrics display ---
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Support",
        levels.get("support", "—")
    )
    c2.metric("Resistance", levels.get("resistance", "—"))
    c3.metric("ORB High", levels.get("orb_high", "—"))
    c4.metric("ORB Low", levels.get("orb_low", "—"))
    c5.metric(
        "Live Resistance",
        f"{live_resistance:.2f}" if live_resistance else "—",
        help="Auto-detected from intraday swing highs"
    )

    # ---- Live Context (single, clean) ----
    context_msgs = []

    if price and levels and all(k in levels for k in ("support", "resistance", "orb_high", "orb_low")):
        if abs(price - levels["resistance"]) / price < 0.003:
            context_msgs.append("⚠️ Price near resistance — breakout or rejection zone.")
        if abs(price - levels["support"]) / price < 0.003:
            context_msgs.append("🟢 Price near support — potential demand zone.")
        if price > levels["orb_high"]:
            context_msgs.append("📈 Above ORB High — bullish momentum.")
        if price < levels["orb_low"]:
            context_msgs.append("📉 Below ORB Low — bearish momentum.")

    if not context_msgs:
        context_msgs.append("ℹ️ Price is between key intraday levels.")

    with st.expander("ℹ️ Live Level Context (Auto-updating)"):
        for msg in context_msgs:
            st.markdown(f"- {msg}")

    st.divider()


    # =====================================================
    # 🔔 ALERTS (PRICE + LEVEL BASED)
    # =====================================================
    alerts = []

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
            help=SECTION_HELP["alerts"]
        )
        for a in new_alerts:
            st.warning(a)


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

    # --- OPTIONAL: Upgrade to LIVE only if truly possible ---
    if IS_LOCAL_DESKTOP and cookie_status == "FRESH":
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

        except Exception:
            st.info("ℹ️ LIVE NSE options unavailable. Showing fallback data.")

    # =====================================================
    # USER STATUS (CLEAN, NON-SCARY)
    # =====================================================
    if IS_LOCAL_DESKTOP and cookie_status != "FRESH":
        st.info(
            "ℹ️ Showing safe, delayed options sentiment.\n\n"
            "Advanced users may enable LIVE NSE options using desktop browser cookies."
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

    # =====================================================
    # 📈 TRADE DECISION ENGINE (UNIFIED – SINGLE SOURCE)
    # =====================================================
    
    from logic.trade_confidence import (
        calculate_trade_confidence,
        confidence_label,
    )
    
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
    
    # --- CONFIDENCE SCORING (ONLY IF ALLOWED) ---
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
    
    # =====================================================
    # 🧠 TRADE DECISION OUTPUT (UI)
    # =====================================================
    
    # ---- PRIMARY: RULE-BASED STATUS (NOT A RECOMMENDATION) ----
    if allowed:
        st.success(
            f"✅ Setup Eligible (Rules Passed) | "
            f"Quality Score: {confidence_score}/100 ({confidence_label_text})"
        )
    else:
        st.error(
            f"🚫 Setup Ineligible (Rules Failed) | Reason: {block_reason}"
        )
    
    # ---- WHY THIS DECISION ----
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
    
    # =====================================================
    # 🤖 ML ADVISORY (SECONDARY – HISTORICAL CONTEXT ONLY)
    # =====================================================
    
    ml_score = st.session_state.get("ml_score")
    
    if ml_score is not None:
        ml_pct = int(ml_score * 100)
    
        st.info(
            f"🤖 **ML Setup Quality (Educational Context Only)**\n\n"
            f"- Historical similarity score: **{ml_pct}/100**\n"
            f"- Derived from past market behavior patterns\n\n"
            f"ℹ️ This score is **not predictive** and **not a recommendation**.\n"
            f"ℹ️ It does not permit, block, or suggest trades.\n"
            f"✔ Final eligibility is always determined by rule-based validation."
        )
    
    # =====================================================
    # 🧪 PAPER TRADE SIMULATOR (EXECUTION CONTROLS)
    # =====================================================
    st.subheader(
        "🧪 Paper Trade Simulator (Educational Only)",
        help=SECTION_HELP["paper_trade"]
    )

    ltp = st.session_state.get("last_price_metric")

    qty = st.number_input(
        "Quantity (Lots / Units)",
        min_value=1,
        step=1
    )

    col1, col2 = st.columns(2)

    # -------------------------
    # BUY / SELL (OPEN POSITION)
    # -------------------------
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
                # Prevent multiple open positions on same symbol
                open_trades = [
                    t for t in load_day_trades()
                    if t["Symbol"] == stock and t["Status"] == "OPEN"
                ]
    
                if open_trades:
                    st.warning("⚠️ An OPEN position already exists for this stock. Exit it first.")
                else:
                    trade_id = generate_trade_id()
                    entry_time = now_ist().strftime("%H:%M:%S")
    
                    trade_row = {
                        "Trade ID": trade_id,
                        "Date": get_trade_date(),
                        "Symbol": stock,
                        "Side": st.session_state.direction,   # BUY or SELL
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
    
                    st.success(
                        f"{action_label} recorded | {stock} @ {ltp} (Paper Trade)"
                    )
    
                    st.session_state.history = load_day_trades()
                    refresh_risk_from_history()
                    st.rerun()

    # -------------------------
    # EXIT (LATEST OPEN POSITION)
    # -------------------------
    with col2:
        if st.button("❌ Close Paper Position", use_container_width=True):
    
            open_trades = [
                t for t in load_day_trades()
                if t["Symbol"] == stock and t["Status"] == "OPEN"
            ]
    
            if not open_trades:
                st.warning("No open position for this stock.")
            elif ltp is None:
                st.error("❌ Live price unavailable.")
            else:
                t = open_trades[-1]  # latest open trade
                exit_time = now_ist().strftime("%H:%M:%S")
    
                # ✅ Correct PnL logic
                if t["Side"] == "BUY":
                    pnl = round((ltp - t["Entry"]) * t["Qty"], 2)
                else:  # SELL (SHORT)
                    pnl = round((t["Entry"] - ltp) * t["Qty"], 2)
    
                update_trade_in_csv(
                    t["Trade ID"],
                    {
                        "Exit": ltp,
                        "PnL": pnl,
                        "Exit Time": exit_time,
                        "Status": "CLOSED",
                    }
                )
    
                st.success(
                    f"❌ Paper position closed | {stock} ({t['Side']}) | PnL ₹{pnl}"
                )
    
                st.session_state.history = load_day_trades()
                refresh_risk_from_history()
                st.rerun()

    # =====================================================
    # 📋 PAPER TRADES – TODAY (OPEN + CLOSED)
    # =====================================================
    st.subheader("📋 Paper Trades – Today")
    
    trades_today = load_day_trades()
    
    open_trades = [t for t in trades_today if t["Status"] == "OPEN"]
    closed_trades = [t for t in trades_today if t["Status"] == "CLOSED"]
    
    # =====================================================
    # NET LIVE PnL (ALL OPEN TRADES) — BUY & SELL SAFE
    # =====================================================
    net_live_pnl = 0.0
    
    for t in open_trades:
        trade_price, _ = get_live_price_fast(t["Symbol"])
    
        if trade_price is None or not isinstance(t.get("Entry"), (int, float)):
            continue
    
        if t["Side"] == "BUY":
            net_live_pnl += (trade_price - t["Entry"]) * t["Qty"]
        else:  # SELL (SHORT)
            net_live_pnl += (t["Entry"] - trade_price) * t["Qty"]
    
    color = "green" if net_live_pnl > 0 else "red" if net_live_pnl < 0 else "gray"
    
    st.markdown(
        f"""
        <h3 style="color:{color}; margin-bottom:0;">
            📈 Net Live PnL (Open Paper Trades): ₹{net_live_pnl:.2f}
        </h3>
        """,
        unsafe_allow_html=True
    )
    st.divider()
    
    # =========================
    # OPEN TRADES
    # =========================
    if open_trades:
        st.markdown("### 🟢 Open Paper Trades")
    
        h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns(
            [1.2, 0.6, 0.6, 1, 1, 1, 1, 0.9, 1.2]
        )
        h1.markdown("**Symbol**")
        h2.markdown("**Side**")
        h3.markdown("**Qty**")
        h4.markdown("**Buy Price**")
        h5.markdown("**Sell Price**")
        h6.markdown("**Live Price**")
        h7.markdown("**Live PnL (₹)**")
        h8.markdown("**Status**")
        h9.markdown("**Action**")
    
        for t in open_trades:
            trade_price, _ = get_live_price_fast(t["Symbol"])
    
            live_pnl = None
            if trade_price is not None:
                if t["Side"] == "BUY":
                    live_pnl = round((trade_price - t["Entry"]) * t["Qty"], 2)
                else:
                    live_pnl = round((t["Entry"] - trade_price) * t["Qty"], 2)
    
            buy_price = t["Entry"] if t["Side"] == "BUY" else "—"
            sell_price = t["Entry"] if t["Side"] == "SELL" else "—"
    
            c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(
                [1.2, 0.6, 0.6, 1, 1, 1, 1, 0.9, 1.2]
            )
    
            c1.write(t["Symbol"])
            c2.write(t["Side"])
            c3.write(t["Qty"])
            c4.write(buy_price)
            c5.write(sell_price)
            c6.write(trade_price if trade_price is not None else "—")
    
            if live_pnl is None:
                c7.write("—")
            elif live_pnl > 0:
                c7.markdown(f"<span style='color:green;'>+₹{live_pnl}</span>", unsafe_allow_html=True)
            elif live_pnl < 0:
                c7.markdown(f"<span style='color:red;'>₹{live_pnl}</span>", unsafe_allow_html=True)
            else:
                c7.write("₹0.00")
    
            c8.write("OPEN")
    
            if c9.button("❌ Exit", key=f"exit_{t['Trade ID']}"):
                exit_price = trade_price
                if exit_price is None:
                    st.error("❌ Live price unavailable for exit.")
                else:
                    exit_time = now_ist().strftime("%H:%M:%S")
                    pnl = round((exit_price - t["Entry"]) * t["Qty"], 2)
    
                    update_trade_in_csv(
                        t["Trade ID"],
                        {
                            "Exit": exit_price,
                            "PnL": pnl,
                            "Exit Time": exit_time,
                            "Status": "CLOSED",
                        }
                    )
    
                    st.success(f"❌ {t['Symbol']} CLOSED | PnL ₹{pnl}")
                    st.session_state.history = load_day_trades()
                    refresh_risk_from_history()
                    st.rerun()
    else:
        st.info("No OPEN trades.")
    
    # =========================
    # CLOSED TRADES
    # =========================
    if closed_trades:
        st.markdown("### 🔵 Closed Paper Trades")
    
        rows = []
        for t in closed_trades:
            buy_price = t["Entry"] if t["Side"] == "BUY" else t["Exit"]
            sell_price = t["Exit"] if t["Side"] == "BUY" else t["Entry"]
    
            rows.append({
                "Symbol": t["Symbol"],
                "Side": t["Side"],
                "Qty": t["Qty"],
                "Buy Price": buy_price,
                "Sell Price": sell_price,
                "PnL (₹)": t["PnL"],
                "Entry Time": t["Entry Time"],
                "Exit Time": t["Exit Time"],
                "Strategy": t["Strategy"],
            })
    
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No CLOSED trades yet today.")
        
    st.caption(
        "ℹ️ All trades shown above are **simulated paper trades only**. "
        "No real orders are placed, no broker integration exists, "
        "and this section is provided strictly for **learning and discipline practice**."
    )

    # =====================================================
    # 📊 TRADE ANALYTICS DASHBOARD
    # =====================================================
    # Always define df_trades safely
    df_trades = pd.DataFrame()

    st.subheader("📊 Trade Analytics")

    closed_trades = [
        t for t in st.session_state.history
        if t.get("Status") == "CLOSED" and isinstance(t.get("PnL"), (int, float))
    ]

    if closed_trades:
        df_trades = pd.DataFrame(closed_trades)

        total_trades = len(df_trades)
        wins = df_trades[df_trades["PnL"] > 0]
        losses = df_trades[df_trades["PnL"] < 0]

        win_rate = (len(wins) / total_trades) * 100
        avg_win = wins["PnL"].mean() if not wins.empty else 0.0
        avg_loss = losses["PnL"].mean() if not losses.empty else 0.0

        expectancy = (win_rate / 100) * avg_win + (1 - win_rate / 100) * avg_loss

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", total_trades)
        c2.metric("Win Rate %", f"{win_rate:.1f}%")
        c3.metric("Avg Win (₹)", f"{avg_win:.2f}")
        c4.metric("Avg Loss (₹)", f"{avg_loss:.2f}")

        st.metric("📐 Expectancy (₹ / trade)", f"{expectancy:.2f}")

    else:
        st.info("ℹ️ No CLOSED trades yet — analytics will appear after exits.")

    # =====================================================
    # 📈 STRATEGY-WISE PERFORMANCE
    # =====================================================
    st.subheader("📈 Strategy-wise PnL")

    if not df_trades.empty:
        strat_df = (
            df_trades.groupby("Strategy", as_index=False)["PnL"]
            .sum()
            .sort_values("PnL", ascending=False)
        )

        st.dataframe(strat_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Strategy performance will appear after trades are CLOSED.")

    # =====================================================
    # ⏱ TIME-OF-DAY PERFORMANCE
    # =====================================================
    st.subheader("⏱ Time-of-Day Performance")

    if not df_trades.empty and "Entry Time" in df_trades.columns:
        df_trades["Hour"] = pd.to_datetime(
            df_trades["Entry Time"],
            format="%H:%M:%S",
            errors="coerce"
        ).dt.hour

        hour_pnl = (
            df_trades.groupby("Hour", as_index=False)["PnL"]
            .sum()
            .rename(columns={"PnL": "Total PnL"})
        )

        st.dataframe(hour_pnl, use_container_width=True)
    else:
        st.info("ℹ️ Time-based stats will appear after trades are CLOSED.")

    # =====================================================
    # HOW TO USE
    # =====================================================
    st.subheader("📘 How to Use This Dashboard")

    with st.expander("Click to read"):
        st.markdown("""
    • Pre-market → mark bias & levels  
    • First 15 min → observe ORB  
    • Trade only with confirmation  
    • Respect daily risk limits  
    • Review, don't revenge trade  
    """)