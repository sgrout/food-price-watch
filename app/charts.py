"""Pure chart builders (tested): data in, plotly figure out. No database access here."""

from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BLUE = "#2a78d6"  # series slot 1 (validated default palette)
BAND80 = "rgba(42, 120, 214, 0.30)"  # same hue, translucent: readable on light and dark surfaces
BAND95 = "rgba(42, 120, 214, 0.14)"
NEUTRAL = "#8a8984"  # between the light and dark secondary-text tokens: reference line and error markers


def month_date(m: int) -> date:
    """Mirror of fpw.panel.month_date (the app ships without the fpw package; a test checks they agree)."""
    return date(int(m) // 12, int(m) % 12 + 1, 15)


def fan_chart(history: pd.DataFrame, forecast: pd.DataFrame | None, currency: str, unit: str) -> go.Figure:
    """Price history and the forecast fan (80 % and 95 % ranges, median), plus the usual level for the season.

    history: date, price, is_suspect.  forecast: target (month index), q025, q10, q50, q90, q975, expected (log).
    """
    fig = go.Figure()
    ok = history[~history["is_suspect"]]
    fig.add_trace(go.Scatter(x=ok["date"], y=ok["price"], mode="lines", name="Price (observed)",
                             line=dict(color=BLUE, width=2), hovertemplate="%{y:,.0f}<extra>observed</extra>"))
    bad = history[history["is_suspect"]]
    if len(bad):
        fig.add_trace(go.Scatter(x=bad["date"], y=bad["price"], mode="markers", name="Data error (not used)",
                                 marker=dict(symbol="x", size=9, color=NEUTRAL),
                                 hovertemplate="%{y:,.0f}<extra>data error</extra>"))
    if forecast is not None and len(forecast):
        f = forecast.sort_values("target")
        x = [month_date(m) for m in f["target"]]
        level = lambda col: np.exp(f[col].to_numpy(dtype=float)).tolist()  # log price -> price
        # The fan starts at the last observed price (width 0), so it shows uncertainty growing from what is known.
        start = ok[pd.to_datetime(ok["date"]) < pd.Timestamp(x[0])].tail(1)
        x0, y0 = (list(start["date"]), [float(start["price"].iloc[0])]) if len(start) else ([], [])
        for lo, hi, colour, name in [("q025", "q975", BAND95, "95 % range"), ("q10", "q90", BAND80, "80 % range")]:
            xs, upper, lower = x0 + x, y0 + level(hi), y0 + level(lo)
            fig.add_trace(go.Scatter(x=xs + xs[::-1], y=upper + lower[::-1], fill="toself",
                                     fillcolor=colour, mode="lines", line=dict(width=0), name=name,
                                     hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x0 + x, y=y0 + level("q50"), mode="lines+markers", name="Forecast (most likely)",
                                 line=dict(color=BLUE, width=2, dash="dot"), marker=dict(size=8, color=BLUE),
                                 customdata=np.column_stack([y0 + level("q10"), y0 + level("q90")]),
                                 hovertemplate="%{y:,.0f} (80 %: %{customdata[0]:,.0f}-%{customdata[1]:,.0f})"
                                               "<extra>forecast</extra>"))
        fig.add_trace(go.Scatter(x=x, y=level("expected"), mode="lines", name="Usual level for the season",
                                 line=dict(color=NEUTRAL, width=2, dash="dash"),
                                 hovertemplate="%{y:,.0f}<extra>usual level</extra>"))
    fig.update_layout(
        template="none", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",  # follow the app theme
        hovermode="x unified", margin=dict(l=60, r=10, t=30, b=40), height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title=f"{currency} per {unit}", rangemode="tozero", gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
    )
    return fig
