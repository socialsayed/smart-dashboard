# =====================================================
# IMPORTS
# =====================================================
import time
import streamlit as st
import os
import pandas as pd
from config import *
from services.market_time import now_ist, market_status, countdown
from services.prices import live_price
from services.options import get_pcr
from services.charts import get_intraday_data
from data.watchlist import daily_watchlist
from logic.levels import calc_levels
from logic.risk import risk_ok
from logic.decision import trade_decision
from utils.cache import init_state
from utils.charts import (
    intraday_candlestick,
    add_vwap
)

from services.nifty_options import (
    get_nifty_option_chain,
    extract_atm_region,
    calculate_pcr,
    options_sentiment
)

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

# =====================================================
# 🔍 SANITY CHECK (INTRADAY DATA)
# =====================================================
def sanity_check_intraday(df, interval, symbol):
    if df is None or df.empty:
        st.warning(f"⚠️ {symbol}: Intraday data unavailable")
        return False

    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        st.warning(f"⚠️ Missing OHLC columns: {missing}")
        return False

    if not hasattr(df.index, "is_monotonic_increasing") or not df.index.is_monotonic_increasing:
        st.warning("⚠️ Intraday candles not time-sorted")

    if df[list(required)].isna().mean().mean() > 0.25:
        st.warning("⚠️ High NaN density in intraday candles")

    if df.iloc[-1][list(required)].isna().any():
        st.warning("⚠️ Latest candle incomplete (live candle)")

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
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Fill missing columns with defaults for backward compatibility
        for col in ["Strategy", "Options Bias", "Market Status", "Notes"]:
            if col not in df.columns:
                df[col] = ""
        return df.to_dict("records")
    return []

def append_trade(row: dict):
    path = get_trade_file()
    df = pd.DataFrame([row])
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", header=header, index=False)


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


@st.cache_data(ttl=5)
def cached_live_price(symbol):
    return live_price(symbol)


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
    return add_vwap(df)



# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# GLOBAL STYLE
# =====================================================
st.info("📱 On mobile: tap ☰ (top-left) to open sidebar controls")
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Keep header + toolbar visible for mobile ☰ */
[data-testid="stHeader"] {
    visibility: visible;
}

/* Optional: hide decoration bar */
[data-testid="stDecoration"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# DISCLAIMER
# =====================================================
with st.expander("⚠️ IMPORTANT DISCLAIMER", expanded=False):
    st.markdown("""
This dashboard is for **market analysis and educational purposes only**.  
It does **NOT execute trades**, does **NOT provide investment advice**,  
and does **NOT guarantee returns**.

Use this tool for structured decision-making, not impulse trading.
""")

# =====================================================
# SESSION STATE
# =====================================================
init_state({
    "open_trade": None,
    "pnl": 0.0,
    "trades": 0,
    "history": [],
    "live_cache": {},
    "alert_state": set(),
    "last_options_bias": None,
    "last_intraday_df": None,
    "levels": {},
    "last_refresh": time.time()
})

# Load persisted paper trades for today
if not st.session_state.history:
    st.session_state.history = load_day_trades()
    if st.session_state.history:
        st.session_state.trades = len(st.session_state.history)
        st.session_state.pnl = sum(t.get("PnL", 0) for t in st.session_state.history)



# =====================================================
# HEADER
# =====================================================
st.title("📊 Smart Intraday Trading Dashboard")
st.caption(
    "A professional intraday decision-support system designed to help traders "
    "analyze price structure, market sentiment, and risk — before taking trades."
)


# =====================================================
# SIDEBAR – MARKET SELECTION
# =====================================================
st.sidebar.header(
    "📌 Market Selection",
    help="Select index and stock. All data updates automatically."
)

index = st.sidebar.selectbox("Select Index", INDEX_MAP.keys())
stock = st.sidebar.selectbox("Select Stock", INDEX_MAP[index])


# =====================================================
# SIDEBAR – RISK LIMITS
# =====================================================
st.sidebar.header(
    "🛡 Risk Limits",
    help="Daily risk controls to enforce discipline."
)

max_trades = st.sidebar.number_input(
    "Max Trades / Day", 1, 10, 3,
    help="Maximum intraday trades allowed."
)

max_loss = st.sidebar.number_input(
    "Max Loss / Day (₹)", 1000, 50000, 5000,
    help="Trading stops once this loss is breached."
)


# =====================================================
# SIDEBAR – STRATEGY MODE
# =====================================================
st.sidebar.header(
    "🧠 Strategy Mode",
    help="Choose the strategy lens for interpretation."
)

strategy = st.sidebar.radio(
    "Choose Strategy",
    ["ORB Breakout", "VWAP Mean Reversion"]
)

if strategy == "ORB Breakout":
    st.sidebar.info(
        "📈 **ORB Breakout Strategy**\n\n"
        "• First 15 minutes define range\n"
        "• Trade break of ORB High / Low\n"
        "• Works best on trending days\n"
        "• Confirm with volume & VWAP"
    )
else:
    st.sidebar.info(
        "📉 **VWAP Mean Reversion Strategy**\n\n"
        "• VWAP = institutional fair price\n"
        "• Trade pullbacks & rejections\n"
        "• Best on balanced / sideways days"
    )

# =====================================================
# ℹ️ SIDEBAR – APP GUIDE / HOW TO USE
# =====================================================
with st.sidebar.expander("ℹ️ App Guide – What This Dashboard Does", expanded=False):

    st.markdown("""
### 🎯 What is this app?
This is a **Smart Intraday Trading Dashboard** designed to help traders make
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


# =====================================================
# MARKET STATUS
# =====================================================
st.subheader(
    "🕒 Market Status",
    help=SECTION_HELP["market_status"]
)

open_now, next_open = market_status()
c1, c2, c3 = st.columns(3)

c1.metric("🇮🇳 IST Time", now_ist().strftime("%d %b %Y, %H:%M:%S"))
c2.metric("Market Status", "🟢 OPEN" if open_now else "🔴 CLOSED")

if not open_now and next_open:
    c3.metric("Next Market Open", next_open.strftime("%d %b %Y %H:%M IST"))
    st.info(f"⏳ Countdown: {countdown(next_open)}")

st.divider()

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

# =====================================================
# LIVE PRICE
# =====================================================
st.subheader(
    "📡 Live Price",
    help=SECTION_HELP["live_price"]
)

price, src = cached_live_price(stock)
if price:
    st.session_state.live_cache[stock] = (price, src)

price, src = st.session_state.live_cache.get(stock, (None, None))
delta = None
last_price = st.session_state.get("last_price_metric")

if last_price and price:
    delta = round(price - last_price, 2)

st.metric(
    stock,
    price if price else "—",
    delta=f"{delta:+}" if delta else None,
    help=f"Source: {src}"
)

if price:
    st.session_state.last_price_metric = price

st.divider()


# =====================================================
# INTRADAY CHART
# =====================================================

result = cached_intraday_data(stock)

if not isinstance(result, tuple) or len(result) != 2:
    df, interval = None, None
else:
    df, interval = result

interval_label = (
    "3-Minute" if interval == "3m"
    else "5-Minute" if interval == "5m"
    else "Intraday"
)

st.subheader(
    f"📊 Intraday Chart ({interval_label})",
    help=SECTION_HELP["intraday_chart"]
)

if sanity_check_intraday(df, interval, stock):
    df = add_vwap(df)
    st.session_state.last_intraday_df = df
else:
    df = st.session_state.last_intraday_df
    if df is not None:
        st.info("ℹ️ Showing last stable intraday data")

# --- Plot chart (FIXED: removed support/resistance parameters) ---
if df is not None and not df.empty:
    fig = intraday_candlestick(df, stock)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Intraday data unavailable at the moment.")

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
watchlist = daily_watchlist(INDEX_MAP[index], today)

rows = []
for sym in watchlist:
    if sym not in st.session_state.live_cache:
        p, sc = cached_live_price(sym)
        st.session_state.live_cache[sym] = (p, sc)
    p, sc = st.session_state.live_cache[sym]
    rows.append({"Stock": sym, "Live Price": p if p else "—", "Source": sc})

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
# OPTIONS SENTIMENT
# =====================================================
st.subheader(
    "🧾 Options Chain (PCR)",
    help=SECTION_HELP["options_pcr"]
)
index_pcr = cached_index_pcr()
st.metric("Put–Call Ratio", index_pcr)

st.divider()


# =====================================================
# NIFTY OPTIONS CHAIN (INTRADAY)
# =====================================================
st.subheader(
    "📊 NIFTY Options Chain (Intraday)",
    help=SECTION_HELP["nifty_options"]
)

try:
    df_options, spot, expiry = cached_nifty_option_chain()
    atm_df, atm, pcr_atm, ce_oi, pe_oi = cached_atm_analysis(df_options, spot)
    sentiment = options_sentiment(
        pcr_atm,
        atm_df["ce_oi_chg"].sum(),
        atm_df["pe_oi_chg"].sum()
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NIFTY Spot", spot)
    c2.metric("ATM Strike", atm)
    c3.metric("PCR (ATM Zone)", pcr_atm)
    c4.metric("Expiry", expiry)

    st.write("**Market Bias:**", sentiment)

    st.dataframe(
        atm_df.sort_values("strike"),
        use_container_width=True
    )

except Exception:
    atm_df = None

    if open_now:
        st.warning(
            "⚠️ Unable to fetch NIFTY options chain right now. "
            "This may be due to NSE rate limits."
        )
    else:
        st.info(
            "🕒 Market is closed. "
            "NIFTY options chain updates during market hours."
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
    ce_oi = atm_df["ce_oi_chg"].sum()
    pe_oi = atm_df["pe_oi_chg"].sum()
    pcr_atm = calculate_pcr(atm_df)

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

    # Update stored bias
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


# =====================================================
# TRADE DECISION
# =====================================================
st.subheader(
    "📈 Trade Decision Engine",
    help=SECTION_HELP["trade_decision"]
)
risk_status = risk_ok(
    st.session_state.trades,
    max_trades,
    st.session_state.pnl,
    max_loss
)

allowed, reason = trade_decision(
    open_now,
    risk_status,
    index_pcr,
    price,
    levels.get("resistance", 0),
    options_bias=options_bias
)

# =====================================================
# ⚠ DISCIPLINE WARNINGS (ADVISORY ONLY)
# =====================================================
discipline_warnings = []

# Overtrading warning
if st.session_state.trades >= max_trades:
    discipline_warnings.append("⚠ Max trades reached — overtrading risk.")

# Revenge trading warning (3 consecutive losses)
if st.session_state.history and len(st.session_state.history) >= 3:
    last_3 = pd.DataFrame(st.session_state.history).tail(3)
    if (last_3["PnL"] < 0).all():
        discipline_warnings.append(
            "⚠ 3 consecutive losses — possible revenge trading."
        )

for w in discipline_warnings:
    st.warning(w)


if allowed:
    st.markdown("<div class='trade-allowed'>✅ TRADE ALLOWED</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='trade-blocked'>🚫 TRADE BLOCKED<br>{reason}</div>", unsafe_allow_html=True)

st.divider()

# =====================================================
# 🧪 PAPER TRADE SIMULATOR
# =====================================================
st.subheader(
    "🧪 Paper Trade Simulator",
    help=SECTION_HELP["paper_trade"]
)

if st.session_state.open_trade is None:
    qty = st.number_input("Quantity (Lots / Units)", min_value=1, step=1)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📈 BUY (Paper Trade)", use_container_width=True):
            if allowed:
                st.session_state.open_trade = {
                    "side": "BUY",
                    "entry_price": price,
                    "qty": qty,
                    "time": now_ist().strftime("%H:%M:%S"),
                    "symbol": stock
                }
                st.success("Paper BUY trade opened")
            else:
                st.error(f"❌ Trade blocked: {reason}")

    with col2:
        if st.button("📉 SELL (Paper Trade)", use_container_width=True):
            if allowed:
                st.session_state.open_trade = {
                    "side": "SELL",
                    "entry_price": price,
                    "qty": qty,
                    "time": now_ist().strftime("%H:%M:%S"),
                    "symbol": stock
                }
                st.success("Paper SELL trade opened")
            else:
                st.error(f"❌ Trade blocked: {reason}")

else:
    trade = st.session_state.open_trade

    pnl = (
        (price - trade["entry_price"]) * trade["qty"]
        if trade["side"] == "BUY"
        else (trade["entry_price"] - price) * trade["qty"]
    )

    st.info(
        f"📌 Open Trade: {trade['side']} {trade['symbol']} @ {trade['entry_price']} | "
        f"Qty: {trade['qty']} | PnL: ₹{pnl:.2f}"
    )

    notes = st.text_area(
        "🧠 Trade Notes / Journal",
        placeholder=(
            "Why did I take this trade?\n"
            "Was it according to plan?\n"
            "Emotion, mistake, lesson, improvement..."
        )
    )

    if st.button("❌ Exit Paper Trade", use_container_width=True):
        exit_time = now_ist().strftime("%H:%M:%S")

        trade_row = {
            "Date": get_trade_date(),
            "Symbol": trade["symbol"],
            "Side": trade["side"],
            "Entry": trade["entry_price"],
            "Exit": price,
            "Qty": trade["qty"],
            "PnL": round(pnl, 2),
            "Entry Time": trade["time"],
            "Exit Time": exit_time,
            "Strategy": strategy,
            "Options Bias": options_bias,
            "Market Status": "OPEN" if open_now else "CLOSED",
            "Notes": notes.strip(),
        }

        append_trade(trade_row)

        st.session_state.pnl += pnl
        st.session_state.trades += 1
        st.session_state.history.append(trade_row)

        st.session_state.open_trade = None
        st.success("✅ Paper trade closed & journal saved")


# =====================================================
# TRADE HISTORY
# =====================================================
st.subheader(
    "📒 Trade History & PnL",
    help=SECTION_HELP["trade_history"]
)

st.metric("PnL Today (₹)", round(st.session_state.pnl, 2))

if st.session_state.history:
    st.dataframe(st.session_state.history, use_container_width=True)
else:
    st.info("No trades recorded yet")

# =====================================================
# 📊 TRADE ANALYTICS DASHBOARD
# =====================================================
st.subheader("📊 Trade Analytics")

if st.session_state.history:
    df_trades = pd.DataFrame(st.session_state.history)

    # Core metrics
    total_trades = len(df_trades)
    wins = df_trades[df_trades["PnL"] > 0]
    losses = df_trades[df_trades["PnL"] < 0]

    win_rate = (len(wins) / total_trades) * 100 if total_trades else 0
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
    st.info("ℹ️ No trades yet — analytics will appear after first trade.")

# =====================================================
# 📈 STRATEGY-WISE PERFORMANCE
# =====================================================
st.subheader("📈 Strategy-wise PnL")

if st.session_state.history:
    strat_df = (
        df_trades.groupby("Strategy")["PnL"]
        .sum()
        .reset_index()
        .sort_values("PnL", ascending=False)
    )

    st.dataframe(strat_df, use_container_width=True)
else:
    st.info("ℹ️ Strategy performance will appear after trades.")

# =====================================================
# ⏱ TIME-OF-DAY PERFORMANCE
# =====================================================
st.subheader("⏱ Time-of-Day Performance")

if st.session_state.history and "Entry Time" in df_trades.columns:
    df_trades["Hour"] = pd.to_datetime(
        df_trades["Entry Time"],
        format="%H:%M:%S",
        errors="coerce"
    ).dt.hour

    hour_pnl = (
        df_trades.groupby("Hour")["PnL"]
        .sum()
        .reset_index()
        .rename(columns={"PnL": "Total PnL"})
    )

    st.dataframe(hour_pnl, use_container_width=True)
else:
    st.info("ℹ️ Time-based stats will appear after trades.")

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


# =====================================================
# AUTO REFRESH (LAST LINE ONLY)
# =====================================================
now_ts = time.time()
REFRESH = LIVE_REFRESH if open_now else 20
if now_ts - st.session_state.last_refresh >= REFRESH:
    st.session_state.last_refresh = now_ts
    st.rerun()
