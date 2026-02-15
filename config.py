import pytz

APP_TITLE = "Smart Intraday Trading Dashboard"
LAYOUT = "wide"

IST = pytz.timezone("Asia/Kolkata")

LIVE_REFRESH = 10      # seconds
LEVEL_REFRESH = 300   # seconds

INDEX_MAP = {
    "NIFTY 50": [
        "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC",
        "LT","AXISBANK","KOTAKBANK","BHARTIARTL","BAJFINANCE",
        "ASIANPAINT","HCLTECH","TITAN"
    ],
    "BANKNIFTY": [
        "HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK",
        "INDUSINDBK","PNB","FEDERALBNK","IDFCFIRSTB","BANDHANBNK"
    ],
    "FINNIFTY": [
        "HDFCBANK","ICICIBANK","AXISBANK","KOTAKBANK",
        "BAJFINANCE","BAJAJFINSV","SBILIFE","HDFCLIFE"
    ]
}
