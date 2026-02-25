# =====================================================
# UNIFIED TRADE EVALUATION PIPELINE
# SINGLE SOURCE OF TRUTH
# =====================================================

from logic.decision import (
    trade_decision,
    calculate_trade_confidence,
    confidence_label,
)
from logic.risk import risk_ok
from logic.levels import calc_levels


def _build_indicator_snapshot(df, price):
    """
    Pure indicator snapshot.
    NO session_state.
    NO Streamlit.
    """

    # --- VWAP ---
    vwap = df["VWAP"].iloc[-1]

    # --- VWAP slope (last 5 candles) ---
    if len(df) >= 5:
        vwap_slope = (df["VWAP"].iloc[-1] - df["VWAP"].iloc[-5]) / df["VWAP"].iloc[-1]
    else:
        vwap_slope = 0

    # --- ORB signal ---
    levels = calc_levels(price)
    orb_signal = (
        "CONFIRMED"
        if price > levels["orb_high"] or price < levels["orb_low"]
        else "NONE"
    )

    # --- Trend alignment ---
    highs = df["High"].tail(5)
    lows = df["Low"].tail(5)

    hh = (highs.diff() > 0).sum()
    hl = (lows.diff() > 0).sum()

    if hh >= 3 and hl >= 3:
        trend_alignment = "STRONG"
    elif hh >= 2:
        trend_alignment = "MILD"
    else:
        trend_alignment = "NONE"

    return {
        "vwap": vwap,
        "vwap_slope": vwap_slope,
        "orb_signal": orb_signal,
        "trend_alignment": trend_alignment,
        "levels": levels,
    }


def evaluate_trade_setup(
    *,
    symbol,
    df,
    price,
    index_pcr,
    options_bias,
    risk_context,
    mode="MANUAL",  # MANUAL | SCANNER
):
    """
    Canonical evaluation used by BOTH:
    - Manual trading
    - Market scanner
    """

    # -------------------------------------------------
    # Indicator snapshot
    # -------------------------------------------------
    snap = _build_indicator_snapshot(df, price)

    # -------------------------------------------------
    # Confidence engine (UNCHANGED)
    # -------------------------------------------------
    confidence_score, confidence_reasons = calculate_trade_confidence({
        "price": price,
        "vwap": snap["vwap"],
        "vwap_slope": snap["vwap_slope"],
        "orb_signal": snap["orb_signal"],
        "trend_alignment": snap["trend_alignment"],
        "pcr": index_pcr,
        "direction": "BUY" if options_bias != "BEARISH" else "SELL",
    })

    # -------------------------------------------------
    # Risk handling
    # -------------------------------------------------
    if mode == "SCANNER":
        risk_status = (True, None)
    else:
        risk_status = risk_ok(
            risk_context["trades"],
            risk_context["max_trades"],
            risk_context["pnl"],
            risk_context["max_loss"],
        )

    # -------------------------------------------------
    # Trade decision engine (UNCHANGED)
    # -------------------------------------------------
    allowed, reason = trade_decision(
        open_now=True,
        risk_status=risk_status,
        index_pcr=index_pcr,
        price=price,
        resistance=snap["levels"]["resistance"],
        options_bias=options_bias,
        confidence_score=confidence_score,
    )

    # -------------------------------------------------
    # Normalize to BUY / WATCH / AVOID
    # -------------------------------------------------
    if not allowed:
        status = "AVOID"
    elif confidence_score >= 70:
        status = "BUY"
    elif confidence_score >= 45:
        status = "WATCH"
    else:
        status = "AVOID"

    return {
        "symbol": symbol,
        "status": status,
        "allowed": allowed,
        "confidence": confidence_score,
        "confidence_label": confidence_label(confidence_score),
        "confidence_reasons": confidence_reasons,
        "block_reason": None if allowed else reason,
    }