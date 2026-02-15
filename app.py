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
    help=(
        "Select the index and stock you want to analyze. "
        "All charts, prices, indicators, and signals update automatically "
        "based on this selection."
    )
)

index = st.sidebar.selectbox("Select Index", INDEX_MAP.keys())
stock = st.sidebar.selectbox("Select Stock", INDEX_MAP[index])


# =====================================================
# SIDEBAR – RISK LIMITS
# =====================================================
st.sidebar.header(
    "🛡 Risk Limits",
    help=(
        "Personal daily risk controls. These limits help enforce discipline "
        "by blocking trades after excessive activity or losses."
    )
)

max_trades = st.sidebar.number_input(
    "Max Trades / Day",
    1, 10, 3,
    help="Maximum number of intraday trades allowed for the day."
)

max_loss = st.sidebar.number_input(
    "Max Loss / Day (₹)",
    1000, 50000, 5000,
    help="Maximum acceptable loss for the day. Trading is blocked if breached."
)


# =====================================================
# SIDEBAR – STRATEGY MODE (NEW)
# =====================================================
st.sidebar.header(
    "🧠 Strategy Mode",
    help="Choose the strategy lens you want to use while reading the chart."
)

strategy = st.sidebar.radio(
    "Choose Strategy",
    ["ORB Breakout", "VWAP Mean Reversion"]
)

if strategy == "ORB Breakout":
    st.sidebar.info(
        "📈 **ORB Breakout Strategy**\n\n"
        "• First 15 minutes define range\n"
        "• Trade break above ORB High or below ORB Low\n"
        "• Best on trending days\n"
        "• Needs volume + VWAP confirmation"
    )
else:
    st.sidebar.info(
        "📉 **VWAP Mean Reversion Strategy**\n\n"
        "• VWAP is institutional fair price\n"
        "• Trade pullbacks & rejections near VWAP\n"
        "• Best on sideways / balanced days"
    )


# =====================================================
# AUTO REFRESH
# =====================================================
now_ts = time.time()
if now_ts - st.session_state.last_refresh >= LIVE_REFRESH:
    st.session_state.last_refresh = now_ts
    st.experimental_rerun()


# =====================================================
# MARKET STATUS
# =====================================================
st.subheader(
    "🕒 Market Status",
    help=(
        "Displays whether the Indian stock market (NSE) is currently open. "
        "Intraday analysis and signals are meaningful only during market hours."
    )
)

open_now, next_open = market_status()
c1, c2, c3 = st.columns(3)

c1.metric(
    "🇮🇳 IST Time",
    now_ist().strftime("%d %b %Y, %H:%M:%S"),
    help="Current Indian Standard Time."
)

c2.metric(
    "Market Status",
    "🟢 OPEN" if open_now else "🔴 CLOSED",
    help="Shows whether NSE trading session is active."
)

if not open_now and next_open:
    c3.metric(
        "Next Market Open",
        next_open.strftime("%d %b %Y %H:%M IST"),
        help="Next scheduled market opening time."
    )
    st.info(f"⏳ Countdown: {countdown(next_open)}")

st.divider()


# =====================================================
# LIVE PRICE
# =====================================================
st.subheader(
    "📡 Live Price",
    help="Latest traded price (LTP) of the selected stock."
)

price, src = live_price(stock)
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
    help=(
        "3-minute candlestick chart with:\n"
        "• VWAP\n"
        "• ORB High / Low\n"
        "• ORB breakout arrows\n"
        "• Volume bars\n\n"
        "Used for intraday structure and momentum analysis."
    )
)

df = get_intraday_data(stock)

if df is not None and not df.empty:
    df = add_vwap(df)
    fig = intraday_candlestick(df, stock)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Intraday data available only during market hours.")

# =====================================================
# WHY THIS SIGNAL? (NEW)
# =====================================================
if strategy == "ORB Breakout":
    with st.expander("❓ Why this ORB signal?"):
        st.markdown("""
**ORB signals are shown because:**

• First 15 minutes define early institutional bias  
• Break beyond ORB High / Low signals momentum  
• Best suited for trending market conditions  

**Before taking a trade, confirm:**
• Volume expansion  
• Price position relative to VWAP  
• Index alignment  
""")

elif strategy == "VWAP Mean Reversion":
    with st.expander("❓ Why VWAP matters here?"):
        st.markdown("""
**VWAP acts as institutional fair value:**

• Price above VWAP → bullish bias  
• Price below VWAP → bearish bias  
• Reversion trades work when price stretches too far  

**Before trading VWAP, check:**
• Distance from VWAP  
• Slowing momentum  
• Market balance  
""")

st.divider()


# =====================================================
# EDUCATIONAL OVERLAY (NEW)
# =====================================================
with st.expander("🎓 Beginner Help: How to Read This Dashboard"):
    st.markdown("""
**Candlesticks**
• Show Open, High, Low, Close  
• Long candles = strong momentum  

**VWAP**
• Institutional average price  
• Above VWAP → bullish bias  
• Below VWAP → bearish bias  

**ORB**
• First 15 minutes define direction  
• Breakout = momentum  
• Rejection = fake move  

**Volume**
• Expansion confirms moves  
• Low volume = weak signal  

**Golden Rules**
• Never trade blindly  
• Respect daily risk limits  
• Fewer trades = better discipline  
""")

st.divider()


# =====================================================
# DAILY WATCHLIST
# =====================================================
st.subheader(
    "🎯 Daily Watchlist",
    help=(
        "Automatically generated list of liquid stocks for the day. "
        "Helps reduce over-trading and keeps focus on high-quality names."
    )
)
today = now_ist().date()
watchlist = daily_watchlist(INDEX_MAP[index], today)

rows = []
for sym in watchlist:
    if sym not in st.session_state.live_cache:
        p, sc = live_price(sym)
        st.session_state.live_cache[sym] = (p, sc)
    p, sc = st.session_state.live_cache[sym]
    rows.append({"Stock": sym, "Live Price": p if p else "—", "Source": sc})

st.dataframe(rows, use_container_width=True)

st.divider()


# =====================================================
# SUPPORT / RESISTANCE
# =====================================================
st.subheader(
    "📌 Live Support & Resistance",
    help=(
        "Dynamic intraday price levels calculated from the current price.\n\n"
        "• Support → potential buying zone\n"
        "• Resistance → potential selling zone\n"
        "• ORB High / Low → opening range boundaries\n\n"
        "Used for trade location and risk management."
    )
)

if price:
    st.session_state.levels = calc_levels(price)

levels = st.session_state.levels
c1, c2, c3, c4 = st.columns(4)

c1.metric("Support", levels.get("support", "—"))
c2.metric("Resistance", levels.get("resistance", "—"))
c3.metric("ORB High", levels.get("orb_high", "—"))
c4.metric("ORB Low", levels.get("orb_low", "—"))

st.divider()


# =====================================================
# OPTIONS SENTIMENT
# =====================================================
st.subheader(
    "🧾 Options Chain (PCR)",
    help=(
        "Put–Call Ratio (PCR) reflects options market sentiment.\n\n"
        "• Higher PCR → bullish bias\n"
        "• Lower PCR → bearish bias\n\n"
        "Used as a background sentiment filter, not a standalone signal."
    )
)

pcr = get_pcr()
st.metric("Put–Call Ratio", pcr)

st.divider()


# =====================================================
# TRADE DECISION
# =====================================================
st.subheader(
    "📈 Trade Decision Engine",
    help=(
        "Final rule-based system that determines whether a trade is allowed.\n\n"
        "Checks:\n"
        "• Market open status\n"
        "• Daily risk limits\n"
        "• Options sentiment (PCR)\n"
        "• Price vs resistance\n\n"
        "Prevents emotional and rule-breaking trades."
    )
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
    pcr,
    price,
    levels.get("resistance", 0)
)

if allowed:
    st.markdown("<div class='trade-allowed'>✅ TRADE ALLOWED</div>",
                unsafe_allow_html=True)
else:
    st.markdown(f"<div class='trade-blocked'>🚫 TRADE BLOCKED<br>{reason}</div>",
                unsafe_allow_html=True)

st.divider()


# =====================================================
# TRADE HISTORY
# =====================================================
st.subheader(
    "📒 Trade History & PnL",
    help=(
        "Tracks simulated intraday trades and cumulative profit or loss.\n\n"
        "Used for self-review, discipline, and performance improvement."
    )
)

st.metric("PnL Today (₹)", round(st.session_state.pnl, 2))

if st.session_state.history:
    st.dataframe(st.session_state.history, use_container_width=True)
else:
    st.info("No trades recorded yet")

st.divider()


# =====================================================
# HOW TO USE
# =====================================================
st.subheader(
    "📘 How to Use This Dashboard",
    help=(
        "Recommended professional workflow for using this dashboard "
        "in a disciplined intraday trading process."
    )
)

with st.expander("Click to read"):
    st.markdown("""
• Pre-market → Mark bias & levels  
• First 15 min → Observe ORB  
• Trade only after confirmation  
• Respect daily risk limits  
• Review, don’t revenge trade  
""")
