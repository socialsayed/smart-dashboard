# =====================================================
# IMPORTS
# =====================================================
import time
import streamlit as st

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
from utils.charts import intraday_candlestick, add_vwap
from services.nifty_options import (
    get_nifty_option_chain,
    extract_atm_region,
    calculate_pcr,
    options_sentiment
)

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
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# =====================================================
# GLOBAL STYLE
# =====================================================
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.trade-allowed {
    background-color: #e8f5e9;
    padding: 14px;
    border-left: 6px solid #2e7d32;
    border-radius: 6px;
}
.trade-blocked {
    background-color: #fdecea;
    padding: 14px;
    border-left: 6px solid #c62828;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# DISCLAIMER
# =====================================================
st.warning(
    "⚠️ **IMPORTANT DISCLAIMER**  \n"
    "This dashboard is for **market analysis and educational purposes only**.\n"
    "It does **NOT execute trades**, does **NOT provide investment advice**, "
    "and **does NOT guarantee returns**.\n\n"
    "Use this tool for structured decision-making, not impulse trading."
)


# =====================================================
# SESSION STATE
# =====================================================
init_state({
    "pnl": 0.0,
    "trades": 0,
    "history": [],
    "live_cache": {},
    "alert_state": set(),
    "levels": {},
    "last_refresh": time.time()
})


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
# MARKET STATUS
# =====================================================
st.subheader(
    "🕒 Market Status",
    help="Shows NSE market state and timing."
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
# LIVE PRICE
# =====================================================
st.subheader("📡 Live Price", help="Latest traded price (LTP).")

price, src = cached_live_price(stock)
if price:
    st.session_state.live_cache[stock] = (price, src)

price, src = st.session_state.live_cache.get(stock, (None, None))
st.metric(stock, price if price else "—", help=f"Source: {src}")

st.divider()


# =====================================================
# INTRADAY CHART
# =====================================================
st.subheader(
    "📊 Intraday Chart (3-Minute)",
    help="3-minute candles with VWAP, ORB, volume, and breakout markers."
)

df = cached_intraday_data(stock)

if df is not None and not df.empty:
    df = cached_add_vwap(df)
    fig = intraday_candlestick(df, stock)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Intraday data available only during market hours.")


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
    help="Key intraday levels used for trade location."
)

last_price = st.session_state.get("last_price")

if price and price != last_price:
    st.session_state.levels = calc_levels(price)
    st.session_state.last_price = price

levels = st.session_state.levels
c1, c2, c3, c4 = st.columns(4)

c1.metric("Support", levels.get("support", "—"))
c2.metric("Resistance", levels.get("resistance", "—"))
c3.metric("ORB High", levels.get("orb_high", "—"))
c4.metric("ORB Low", levels.get("orb_low", "—"))

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
    st.subheader("🔔 Alerts")
    for a in new_alerts:
        st.warning(a)

# =====================================================
# OPTIONS SENTIMENT
# =====================================================
st.subheader("🧾 Options Chain (PCR)", help="Options sentiment indicator.")

index_pcr = cached_index_pcr()
st.metric("Put–Call Ratio", index_pcr)

st.divider()


# =====================================================
# NIFTY OPTIONS CHAIN (INTRADAY)
# =====================================================
st.subheader(
    "📊 NIFTY Options Chain (Intraday)",
    help="ATM & nearby strikes OI, PCR, and writing activity for intraday bias."
)

try:
    df, spot, expiry = cached_nifty_option_chain()
    atm_df, atm, pcr_atm, ce_oi, pe_oi = cached_atm_analysis(df, spot)
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
    st.warning(
        "NIFTY options chain unavailable at the moment. "
        "This can happen outside market hours or due to NSE rate limits."
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
    if pcr_atm > 1.1 and pe_oi > abs(ce_oi):
        options_bias = "BULLISH"
    elif pcr_atm < 0.9 and ce_oi > abs(pe_oi):
        options_bias = "BEARISH"

st.caption(f"🧠 Options Bias: **{options_bias}**")

# =====================================================
# TRADE DECISION
# =====================================================
st.subheader("📈 Trade Decision Engine", help="Final rule-based trade gate.")

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


if allowed:
    st.markdown("<div class='trade-allowed'>✅ TRADE ALLOWED</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='trade-blocked'>🚫 TRADE BLOCKED<br>{reason}</div>", unsafe_allow_html=True)

st.divider()


# =====================================================
# TRADE HISTORY
# =====================================================
st.subheader("📒 Trade History & PnL", help="Session performance tracking.")

st.metric("PnL Today (₹)", round(st.session_state.pnl, 2))

if st.session_state.history:
    st.dataframe(st.session_state.history, use_container_width=True)
else:
    st.info("No trades recorded yet")


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
• Review, don’t revenge trade  
""")


# =====================================================
# AUTO REFRESH (LAST LINE ONLY)
# =====================================================
now_ts = time.time()
REFRESH = LIVE_REFRESH if open_now else 20
if now_ts - st.session_state.last_refresh >= REFRESH:
    st.session_state.last_refresh = now_ts
    st.rerun()