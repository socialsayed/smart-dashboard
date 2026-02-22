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
            # Levels
            # ---------------------------------
            levels = calc_levels(price)

            # ---------------------------------
            # Simple rule-based signals
            # ---------------------------------
            above_orb = price > levels.get("orb_high", float("inf"))
            below_orb = price < levels.get("orb_low", 0)

            reasons = []

            if above_orb:
                reasons.append("ORB High breakout")
            if below_orb:
                reasons.append("ORB Low breakdown")

            # ---------------------------------
            # Trend strength
            # ---------------------------------
            highs = df["High"].tail(5)
            lows = df["Low"].tail(5)

            hh = (highs.diff() > 0).sum()
            hl = (lows.diff() > 0).sum()

            if hh >= 3 and hl >= 3:
                trend_strength = 2
                reasons.append("Strong uptrend")
            elif hh >= 2:
                trend_strength = 1
                reasons.append("Mild uptrend")
            else:
                trend_strength = 0

            # ---------------------------------
            # Rule-based confidence
            # ---------------------------------
            confidence = min(
                100,
                40
                + (20 if above_orb else 0)
                + (20 if trend_strength == 2 else 10 if trend_strength == 1 else 0)
            )

            # ---------------------------------
            # Status
            # ---------------------------------
            if confidence >= 70:
                status = "BUY"
            elif confidence >= 45:
                status = "WATCH"
            else:
                status = "AVOID"

            # ---------------------------------
            # ML FEATURE VECTOR
            # ---------------------------------
            feature_context = {
                "price": price,
                "vwap": df["VWAP"].iloc[-1],
                "vwap_slope": (
                    (df["VWAP"].iloc[-1] - df["VWAP"].iloc[-5])
                    / df["VWAP"].iloc[-1]
                    if len(df) >= 5 else 0
                ),
                "support": levels.get("support"),
                "resistance": levels.get("resistance"),
                "above_orb_high": above_orb,
                "below_orb_low": below_orb,
                "trend_strength": trend_strength,
                "index_pcr": get_pcr() or 1.0,
                "options_bias": 0,  # neutral for scanner
                "minutes_since_open": int(
                    (df.index[-1].timestamp() - df.index[0].timestamp()) / 60
                ),
                "trades_today": 0,
                "current_pnl": 0.0,
            }

            # ---------------------------------
            # ML SCORE (SAFE)
            # ---------------------------------
            try:
                ml_score = score_setup(
                    build_feature_vector(feature_context)
                )
            except Exception:
                ml_score = None

            # ---------------------------------
            # FINAL RESULT
            # ---------------------------------
            results.append({
                "symbol": symbol,
                "status": status,
                "confidence": confidence,
                "reasons": reasons,
                "ml_score": ml_score,   # ✅ EXACTLY WHAT YOU ASKED
            })

        except Exception:
            continue

    return results