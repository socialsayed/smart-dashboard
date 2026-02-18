# services/nifty_options.py

import requests
import pandas as pd
import time

# ---------------- NSE Option Chain ----------------

NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json",
    "Connection": "keep-alive",
}

# ---------------- Persistent NSE Session ----------------

_nse_session = None


def _get_nse_session():
    global _nse_session

    if _nse_session is None:
        s = requests.Session()
        s.headers.update(HEADERS)

        # Prime cookies (CRITICAL for NSE)
        try:
            s.get("https://www.nseindia.com", timeout=5)
        except Exception:
            pass

        _nse_session = s

    return _nse_session


# ---------------- SAFE Option Chain Fetch ----------------

def get_nifty_option_chain():
    """
    Returns:
        df_options (DataFrame),
        spot (float),
        expiry (str)

    Raises:
        RuntimeError only if NSE is completely unavailable
    """

    session = _get_nse_session()
    last_error = None

    for attempt in range(3):  # retry with backoff
        try:
            r = session.get(NSE_URL, timeout=5)

            if r.status_code == 200:
                data = r.json()
                records = data.get("records", {})

                spot = records.get("underlyingValue")
                expiry_dates = records.get("expiryDates", [])
                rows_raw = records.get("data", [])

                if not spot or not expiry_dates or not rows_raw:
                    raise ValueError("Incomplete NSE response")

                expiry = expiry_dates[0]
                rows = []

                for rec in rows_raw:
                    if rec.get("expiryDate") != expiry:
                        continue

                    strike = rec.get("strikePrice")
                    ce = rec.get("CE", {})
                    pe = rec.get("PE", {})

                    rows.append({
                        "strike": strike,
                        "ce_oi": ce.get("openInterest", 0),
                        "ce_oi_chg": ce.get("changeinOpenInterest", 0),
                        "ce_ltp": ce.get("lastPrice", 0),
                        "pe_oi": pe.get("openInterest", 0),
                        "pe_oi_chg": pe.get("changeinOpenInterest", 0),
                        "pe_ltp": pe.get("lastPrice", 0),
                    })

                if rows:
                    return pd.DataFrame(rows), spot, expiry

                last_error = "Empty option rows"

            else:
                last_error = f"HTTP {r.status_code}"

        except Exception as e:
            last_error = str(e)

        time.sleep(1 + attempt)

    # Hard failure ONLY after retries
    return None, None, None


# ---------------- ATM + Nearby Strikes ----------------

def extract_atm_region(df, spot, width=2):
    atm = round(spot / 50) * 50
    strikes = [atm + i * 50 for i in range(-width, width + 1)]
    return df[df["strike"].isin(strikes)], atm


# ---------------- PCR & Sentiment ----------------

def calculate_pcr(df):
    total_ce = df["ce_oi"].sum()
    total_pe = df["pe_oi"].sum()

    if total_ce == 0:
        return None

    return round(total_pe / total_ce, 2)


def options_sentiment(pcr, ce_chg, pe_chg):
    if pcr is None:
        return "⚪ Data unavailable"

    if pe_chg > abs(ce_chg) and pcr > 1:
        return "🟢 Bullish (Put writing)"

    if ce_chg > abs(pe_chg) and pcr < 1:
        return "🔴 Bearish (Call writing)"

    return "⚪ Neutral / Range"
