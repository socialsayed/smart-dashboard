# =====================================================
# MARKET OPPORTUNITY SCANNER (UNIFIED, CANONICAL)
# =====================================================

from logic.evaluate_setup import evaluate_trade_setup

# --- Data & indicators ---
from services.charts import get_intraday_data
from utils.charts import add_vwap
from services.options import get_pcr

# --- ML (advisory only) ---
from ml.features.feature_builder import build_feature_vector
from ml.inference.setup_scorer import score_setup


def run_market_opportunity_scanner(symbols):
    """
    Scans a list of symbols and returns trade-quality assessments.
    ML score is advisory only.
    """

    results = []

    for symbol in symbols:
        try:
            # ---------------------------------
            # Fetch intraday data
            # ---------------------------------
            df, interval = get_intraday_data(symbol)
            if df is None or df.empty:
                continue

            df = add_vwap(df)

            price = df["Close"].iloc[-1]

            # ---------------------------------
            # Unified evaluation (SINGLE SOURCE)
            # ---------------------------------
            result = evaluate_trade_setup(
                symbol=symbol,
                df=df,
                price=price,
                index_pcr=get_pcr() or 1.0,
                options_bias="NEUTRAL",
                risk_context={},   # ignored in SCANNER mode
                mode="SCANNER",
            )

            # ---------------------------------
            # ML score (ADVISORY ONLY)
            # ---------------------------------
            try:
                ml_score = score_setup(
                    build_feature_vector({
                        "price": price,
                        "vwap": df["VWAP"].iloc[-1],
                        "vwap_slope": (
                            (df["VWAP"].iloc[-1] - df["VWAP"].iloc[-5])
                            / df["VWAP"].iloc[-1]
                            if len(df) >= 5 else 0
                        ),
                        "support": None,
                        "resistance": None,
                        "index_pcr": get_pcr() or 1.0,
                        "options_bias": 0,
                        "minutes_since_open": 0,
                        "trades_today": 0,
                        "current_pnl": 0.0,
                    })
                )
            except Exception:
                ml_score = None

            result["ml_score"] = ml_score
            results.append(result)

        except Exception:
            # Scanner must NEVER crash the app
            continue

    return results