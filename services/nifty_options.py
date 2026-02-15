# services/nifty_options.py

import requests
import pandas as pd

# ---------------- NSE Option Chain ----------------

NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}


def get_nifty_option_chain():
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=HEADERS)

    r = session.get(NSE_URL, headers=HEADERS, timeout=5)
    data = r.json()

    spot = data["records"]["underlyingValue"]
    expiry = data["records"]["expiryDates"][0]

    rows = []
    for rec in data["records"]["data"]:
        if rec.get("expiryDate") != expiry:
            continue

        strike = rec["strikePrice"]

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

    return pd.DataFrame(rows), spot, expiry


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
