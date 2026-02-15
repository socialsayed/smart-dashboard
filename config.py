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
LIVE_REFRESH = 10


# =====================================================
# TIMEZONE
# =====================================================
IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# INDEX MAP (TOP ~300 INDIAN STOCKS)
# =====================================================
INDEX_MAP = {
    "NIFTY 50": [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
        "ITC", "LT", "AXISBANK", "KOTAKBANK", "HINDUNILVR",
        "BHARTIARTL", "BAJFINANCE", "ASIANPAINT", "HCLTECH",
        "TITAN", "MARUTI", "SUNPHARMA", "ULTRACEMCO", "NTPC",
        "POWERGRID", "NESTLEIND", "ONGC", "ADANIENT", "ADANIPORTS",
        "WIPRO", "JSWSTEEL", "TATAMOTORS", "COALINDIA", "BPCL",
        "INDUSINDBK", "BAJAJFINSV", "HDFCLIFE", "SBILIFE",
        "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM",
        "HEROMOTOCO", "BRITANNIA", "HINDALCO", "TATASTEEL",
        "APOLLOHOSP", "CIPLA", "M&M", "SHREECEM",
        "TECHM", "UPL"
    ],

    "NIFTY NEXT 50": [
        "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA",
        "BANDHANBNK", "BERGEPAINT", "BIOCON", "BOSCHLTD",
        "CANBK", "CHOLAFIN", "COLPAL", "DABUR",
        "DLF", "GAIL", "GODREJCP", "HAVELLS",
        "ICICIPRULI", "IGL", "INDIGO", "JINDALSTEL",
        "LTFH", "LICHSGFIN", "LUPIN", "MARICO",
        "MUTHOOTFIN", "NAUKRI", "NMDC", "PAGEIND",
        "PETRONET", "PIDILITIND", "PNB", "SIEMENS",
        "SRF", "TATACOMM", "TORNTPHARM", "TVSMOTOR",
        "UBL", "VEDL", "VOLTAS", "ZEEL"
    ],

    "NIFTY MIDCAP 100": [
        "ABCAPITAL", "ALKEM", "ASHOKLEY", "ASTRAL",
        "ATUL", "BAJAJHLDNG", "BALKRISIND", "BEL",
        "BHARATFORG", "BHEL", "CANFINHOME", "COFORGE",
        "CONCOR", "CROMPTON", "CUMMINSIND", "ESCORTS",
        "EXIDEIND", "FEDERALBNK", "GLENMARK", "HAL",
        "HINDPETRO", "IDFCFIRSTB", "IRCTC", "JUBLFOOD",
        "LALPATHLAB", "LICI", "LTTS", "MFSL",
        "MPHASIS", "OBEROIRLTY", "PERSISTENT", "POLYCAB",
        "SAIL", "SUNTV", "TATACHEM", "TATAPOWER",
        "TORNTPOWER", "TRENT", "UNITDSPR", "ZOMATO"
    ],

    "NIFTY SMALLCAP 100": [
        "AARTIIND", "AFFLE", "BALAMINES", "BIRLACORPN",
        "CAMS", "CLEAN", "CYIENT", "DEEPAKNTR",
        "EDELWEISS", "ELGIEQUIP", "FINEORG",
        "GRANULES", "GSPL", "HFCL", "IEX",
        "INDIACEM", "IRB", "JBCHEPHARM",
        "JKCEMENT", "KALYANKJIL", "KEI",
        "KPITTECH", "LATENTVIEW", "MAHLOG",
        "METROPOLIS", "NBCC", "NIITLTD",
        "POLYMED", "RAILTEL", "ROUTE",
        "SONACOMS", "SPANDANA", "STAR",
        "SUPREMEIND", "TATAELXSI", "TRIDENT",
        "VGUARD", "WELCORP"
    ]
}
