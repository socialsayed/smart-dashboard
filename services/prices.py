import requests
import yfinance as yf

HEADERS = {"User-Agent": "Mozilla/5.0"}

def nse_price(symbol):
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        r = s.get(
            f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
            headers=HEADERS,
            timeout=5
        )
        return r.json()["priceInfo"]["lastPrice"], "NSE"
    except:
        return None, None

def yahoo_price(symbol):
    try:
        t = yf.Ticker(f"{symbol}.NS")
        return t.fast_info["last_price"], "Yahoo"
    except:
        return None, None

def live_price(symbol):
    p, src = nse_price(symbol)
    if p:
        return p, src
    return yahoo_price(symbol)
