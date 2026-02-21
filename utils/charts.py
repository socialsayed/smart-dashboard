import plotly.graph_objects as go
import pandas as pd


# =====================================================
# VWAP CALCULATION
# =====================================================
def add_vwap(df: pd.DataFrame):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df


# =====================================================
# ORB CALCULATION (PROTECTED)
# =====================================================
def calc_orb(df: pd.DataFrame, minutes=15, interval_minutes=5):
    candles = max(1, minutes // interval_minutes)

    if len(df) < candles:
        return None

    orb_df = df.iloc[:candles]
    return {
        "high": orb_df["High"].max(),
        "low": orb_df["Low"].min(),
        "end_index": candles - 1
    }


# =====================================================
# ORB BREAKOUT DETECTION
# =====================================================
def detect_orb_breakout(df: pd.DataFrame, orb: dict):
    """
    Detects first ORB breakout or breakdown after ORB window.
    Returns a list of signal dictionaries.
    """
    signals = []

    for i in range(orb["end_index"] + 1, len(df)):
        candle = df.iloc[i]

        # Bullish breakout
        if candle["Close"] > orb["high"]:
            signals.append({
                "type": "bullish",
                "time": candle["Datetime"],
                "price": candle["Close"],
                "reason": (
                    f"Close ₹{candle['Close']:.2f} "
                    f"above ORB High ₹{orb['high']:.2f}"
                )
            })
            break

        # Bearish breakdown
        if candle["Close"] < orb["low"]:
            signals.append({
                "type": "bearish",
                "time": candle["Datetime"],
                "price": candle["Close"],
                "reason": (
                    f"Close ₹{candle['Close']:.2f} "
                    f"below ORB Low ₹{orb['low']:.2f}"
                )
            })
            break

    return signals


# =====================================================
# INTRADAY CHART WITH ORB BREAKOUT ARROWS
# =====================================================
def intraday_candlestick(
    df: pd.DataFrame,
    symbol: str,
    interval_label: str = "Intraday"
):
    fig = go.Figure()

    # =========================
    # PRICE CANDLES
    # =========================
    fig.add_trace(
        go.Candlestick(
            x=df["Datetime"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            hovertemplate=(
                "<b>%{x|%H:%M}</b><br>"
                "Open: ₹%{open:.2f}<br>"
                "High: ₹%{high:.2f}<br>"
                "Low: ₹%{low:.2f}<br>"
                "Close: ₹%{close:.2f}"
                "<extra></extra>"
            )
        )
    )

    # =========================
    # VWAP
    # =========================
    fig.add_trace(
        go.Scatter(
            x=df["Datetime"],
            y=df["VWAP"],
            mode="lines",
            name="VWAP",
            line=dict(color="blue", width=2),
            hovertemplate=(
                "<b>%{x|%H:%M}</b><br>"
                "VWAP: ₹%{y:.2f}<br>"
                "<i>Volume Weighted Avg Price</i>"
                "<extra></extra>"
            )
        )
    )

    # =========================
    # VOLUME BARS
    # =========================
    colors = [
        "green" if c >= o else "red"
        for o, c in zip(df["Open"], df["Close"])
    ]

    fig.add_trace(
        go.Bar(
            x=df["Datetime"],
            y=df["Volume"],
            name="Volume",
            marker_color=colors,
            yaxis="y2",
            opacity=0.35,
            hovertemplate=(
                "<b>%{x|%H:%M}</b><br>"
                "Volume: %{y:,}"
                "<extra></extra>"
            )
        )
    )

    # =========================
    # ORB LEVELS + BREAKOUTS
    # =========================
    orb = calc_orb(df)
    if orb:
        fig.add_hline(
            y=orb["high"],
            line_dash="dash",
            line_color="green",
            annotation_text="ORB High"
        )

        fig.add_hline(
            y=orb["low"],
            line_dash="dash",
            line_color="red",
            annotation_text="ORB Low"
        )

        signals = detect_orb_breakout(df, orb)

        for s in signals:
            fig.add_trace(
                go.Scatter(
                    x=[s["time"]],
                    y=[s["price"]],
                    mode="markers",
                    marker=dict(
                        symbol="triangle-up" if s["type"] == "bullish" else "triangle-down",
                        size=16,
                        color="green" if s["type"] == "bullish" else "red"
                    ),
                    name="ORB Breakout" if s["type"] == "bullish" else "ORB Breakdown",
                    hovertemplate=(
                        "<b>ORB Signal</b><br>"
                        f"{s['reason']}<br>"
                        "<extra></extra>"
                    )
                )
            )

    # =========================
    # LAYOUT (FIXED)
    # =========================
    fig.update_layout(
        title=dict(
            text=f"{symbol} – {interval_label} | VWAP + ORB + Breakouts",
            x=0.01,
            y=0.93,              # 👈 PUSH TITLE DOWN
            xanchor="left",
            yanchor="top"
        ),
        height=620,
        xaxis=dict(domain=[0, 1]),
        yaxis=dict(title="Price", domain=[0.28, 1]),
        yaxis2=dict(
            title="Volume",
            domain=[0, 0.22],
            showgrid=False
        ),
        xaxis_rangeslider_visible=False,

        # Extra top margin to avoid collision
        margin=dict(l=20, r=20, t=110, b=20),

        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.05,              # 👈 LEGEND ABOVE TITLE
            xanchor="left",
            x=0
        ),

        hovermode="x unified"
    )

    return fig
