import requests
import yfinance as yf
import logging

logger = logging.getLogger("SIDB")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# --------------------------------------------------
# NSE DIRECT API
# --------------------------------------------------

def nse_price(symbol):
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=5)

        r = s.get(
            f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
            headers=HEADERS,
            timeout=5
        )

        if r.status_code != 200:
            logger.warning(f"NSE price HTTP {r.status_code} for {symbol}")
            return None, None

        data = r.json()
        price = data.get("priceInfo", {}).get("lastPrice")

        if price is None:
            logger.warning(f"NSE price missing lastPrice for {symbol}")
            return None, None

        return price, "NSE"

    except requests.Timeout:
        logger.warning(f"NSE price timeout for {symbol}")
        return None, None

    except Exception as e:
        logger.exception(f"NSE price failure for {symbol}")
        return None, None


# --------------------------------------------------
# YAHOO FALLBACK
# --------------------------------------------------

def yahoo_price(symbol):
    try:
        t = yf.Ticker(f"{symbol}.NS")
        price = t.fast_info.get("last_price")

        if price is None:
            logger.warning(f"Yahoo price missing last_price for {symbol}")
            return None, None

        return price, "Yahoo"

    except Exception:
        logger.exception(f"Yahoo price failure for {symbol}")
        return None, None


# --------------------------------------------------
# LIVE PRICE ROUTER
# --------------------------------------------------

def live_price(symbol):
    p, src = nse_price(symbol)

    if p:
        return p, src

    logger.info(f"Falling back to Yahoo for {symbol}")
    return yahoo_price(symbol)


# --------------------------------------------------
# BACKWARD COMPATIBILITY
# --------------------------------------------------

def get_live_price(symbol):
    return live_price(symbol)[0]