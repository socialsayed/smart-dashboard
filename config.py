# =====================================================
# CONFIG — SINGLE SOURCE OF TRUTH
# =====================================================
import pytz

# =====================================================
# APP SETTINGS
# =====================================================
APP_TITLE = "Smart Intraday Trading Dashboard"
LAYOUT = "wide"

# Auto refresh interval (seconds)
LIVE_REFRESH = 3   # seconds (recommended 2–5)


# =====================================================
# TIMEZONE
# =====================================================
IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# INDEX → STOCK UNIVERSE MAP
# =====================================================

INDEX_MAP = {

    # -----------------------------
    # NIFTY 50
    # -----------------------------
    "NIFTY 50": [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT",
        "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV",
        "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA",
        "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
        "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
        "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
        "INDUSINDBK", "INFY", "ITC", "JSWSTEEL",
        "KOTAKBANK", "LT", "M&M", "MARUTI",
        "NESTLEIND", "NTPC", "ONGC", "POWERGRID",
        "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA",
        "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM",
        "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
    ],

    # -----------------------------
    # BANK NIFTY
    # -----------------------------
    "BANKNIFTY": [
        "AXISBANK", "BANDHANBNK", "FEDERALBNK",
        "HDFCBANK", "ICICIBANK", "IDFCFIRSTB",
        "INDUSINDBK", "KOTAKBANK", "PNB", "SBIN"
    ],

    # -----------------------------
    # FIN NIFTY
    # -----------------------------
    "FINNIFTY": [
        "BAJAJFINSV", "BAJFINANCE", "CHOLAFIN",
        "HDFCAMC", "HDFCLIFE", "ICICIGI",
        "ICICIPRULI", "LICI", "MUTHOOTFIN",
        "SBILIFE"
    ],

    # -----------------------------
    # NIFTY IT
    # -----------------------------
    "NIFTY IT": [
        "COFORGE", "HCLTECH", "INFY",
        "LTIM", "MPHASIS", "PERSISTENT",
        "TCS", "TECHM", "WIPRO"
    ],

    # -----------------------------
    # NIFTY FMCG
    # -----------------------------
    "NIFTY FMCG": [
        "BRITANNIA", "COLPAL", "DABUR",
        "GODREJCP", "HINDUNILVR", "ITC",
        "MARICO", "NESTLEIND", "TATACONSUM"
    ],

    # -----------------------------
    # NIFTY METAL
    # -----------------------------
    "NIFTY METAL": [
        "ADANIENT", "HINDALCO", "JSWSTEEL",
        "JINDALSTEL", "NALCO", "NMDC",
        "SAIL", "TATASTEEL", "VEDL"
    ],

    # -----------------------------
    # NIFTY ENERGY
    # -----------------------------
    "NIFTY ENERGY": [
        "ADANIPORTS", "BPCL", "COALINDIA",
        "GAIL", "IOC", "NTPC",
        "ONGC", "POWERGRID", "RELIANCE"
    ],

    # -----------------------------
    # NIFTY AUTO
    # -----------------------------
    "NIFTY AUTO": [
        "ASHOKLEY", "BAJAJ-AUTO", "BHARATFORG",
        "EICHERMOT", "HEROMOTOCO", "M&M",
        "MARUTI", "TATAMOTORS", "TVSMOTOR"
    ],

    # -----------------------------
    # NIFTY PHARMA
    # -----------------------------
    "NIFTY PHARMA": [
        "ALKEM", "APOLLOHOSP", "AUROPHARMA",
        "CIPLA", "DIVISLAB", "DRREDDY",
        "LUPIN", "SUNPHARMA", "TORNTPHARM"
    ],

    # -----------------------------
    # MIDCAP (LIQUID)
    # -----------------------------
    "NIFTY MIDCAP": [
        "ADANIENT", "AUBANK", "CANBK",
        "FEDERALBNK", "GODREJPROP",
        "INDIGO", "IRCTC", "LICI",
        "PNB", "TRENT", "ZOMATO"
    ],

    # -----------------------------
    # SMALLCAP (LIQUID / POPULAR)
    # -----------------------------
    "NIFTY SMALLCAP": [
        "IDEA", "IRFC", "RPOWER",
        "SUZLON", "YESBANK"
    ],
}
