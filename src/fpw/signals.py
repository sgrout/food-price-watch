"""Market signals: facts at the data cutoff, not forecasts (no skill is claimed).

1. Distance from the national price: a series' price vs the national median of the same food (country, commodity,
   unit, retail) in the same month, and vs the market's own usual distance. Remote markets are always dearer, so
   the signal is a gap that widens; data errors can look like gaps too.
2. Markets that stopped reporting: months since a market's last price, counted from the country's reference month
   (the latest month most of its markets reported), so late publication by WFP or one early-published month does
   not look like silence.

Input: fpw.panel.monthly_panel (staples, retail, suspect_from). Only observations up to `data_up_to` and without a
known data error by then are used; later months never change the result.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_MARKETS = 5  # markets with a price that month for a national median
USUAL_WINDOW, MIN_USUAL = 36, 12  # the usual gap: median over the 36 months before, at least 12 of them
FAR_ABOVE_GAP = float(np.log(1.25))  # highlighted: at least 25 % above the national median ...
FAR_ABOVE_WIDENING = 0.20  # ... and at least 0.20 (log) above the market's usual gap
REFERENCE_SHARE, ACTIVE_WINDOW = 0.5, 12  # reference month: half the markets active in the 12 months before reported
SILENT_AFTER, LISTED_UP_TO, MIN_MONTHS = 2, 24, 12  # silent: 2+ months; listed up to 24 months, >= 12 months of data
MEDIAN_MONTHS = 36  # national median exported for the last 36 months (the site's chart shows 2 years)


def usable(panel: pd.DataFrame, data_up_to: int) -> pd.DataFrame:
    p = panel[panel["m"] <= data_up_to]
    return p[~(p["suspect_from"] <= data_up_to)]  # NaN (never suspect) compares False: kept


def reference_months(panel: pd.DataFrame, data_up_to: int) -> dict[str, int]:
    """Per country: the latest month <= data_up_to in which at least half of the markets that reported in the 12
    months before it have a price (fallback: its latest month)."""
    p = usable(panel, data_up_to)[["country", "market_id", "m"]].drop_duplicates()
    out = {}
    for country, g in p.groupby("country"):
        out[country] = int(g["m"].max())
        for month in range(int(g["m"].max()), int(g["m"].max()) - ACTIVE_WINDOW, -1):
            active = g.loc[(g["m"] >= month - ACTIVE_WINDOW) & (g["m"] < month), "market_id"].unique()
            if len(active) and g.loc[(g["m"] == month) & g["market_id"].isin(active), "market_id"].nunique() \
                    >= REFERENCE_SHARE * len(active):
                out[country] = month
                break
    return out


def market_silence(panel: pd.DataFrame, data_up_to: int, reference: dict[str, int]) -> pd.DataFrame:
    """One row per market: last month with any price, months silent (vs the reference month), silent, listed."""
    p = usable(panel, data_up_to)
    g = p.sort_values("m").groupby(["country", "market_id"])
    out = g.agg(market=("market", "last"), last_month=("m", "max"), n_months=("m", "nunique")).reset_index()
    out["months"] = (out["country"].map(reference) - out["last_month"]).clip(lower=0).astype(int)
    out["silent"] = out["months"] >= SILENT_AFTER
    out["listed"] = out["silent"] & (out["months"] <= LISTED_UP_TO) & (out["n_months"] >= MIN_MONTHS)
    return out


def national_medians(panel: pd.DataFrame, data_up_to: int) -> pd.DataFrame:
    """Median price per (country, series_commodity_id, unit, month) over markets with a price, n >= MIN_MARKETS."""
    p = usable(panel, data_up_to)
    g = p.groupby(["country", "series_commodity_id", "unit", "m"]).agg(
        median_lp=("lp", "median"), n_markets=("market_id", "nunique")).reset_index()
    return g[g["n_markets"] >= MIN_MARKETS].reset_index(drop=True)


def series_gaps(panel: pd.DataFrame, medians: pd.DataFrame, data_up_to: int) -> pd.DataFrame:
    """Per series, at its last usable month: log gap to the national median, the usual log gap (median over the
    USUAL_WINDOW months before, >= MIN_USUAL of them), the number of markets, and the highlight flag."""
    key = ["country", "series_commodity_id", "unit", "m"]
    p = usable(panel, data_up_to).merge(medians, on=key, how="inner")
    p = p.assign(gap=p["lp"] - p["median_lp"])
    last = usable(panel, data_up_to).groupby("series_id")["m"].max()
    rows = []
    for sid, g in p.groupby("series_id"):
        m_last = int(last[sid])
        now = g[g["m"] == m_last]
        if now.empty:
            continue
        before = g[(g["m"] >= m_last - USUAL_WINDOW) & (g["m"] < m_last)]["gap"]
        gap = float(now["gap"].iloc[0])
        usual = float(before.median()) if len(before) >= MIN_USUAL else np.nan
        rows.append({"series_id": sid, "month": m_last, "gap": gap, "usual_gap": usual,
                     "n_markets": int(now["n_markets"].iloc[0]),
                     "far_above_usual": bool(gap >= FAR_ABOVE_GAP and pd.notna(usual)
                                             and gap - usual >= FAR_ABOVE_WIDENING)})
    return pd.DataFrame(rows, columns=["series_id", "month", "gap", "usual_gap", "n_markets", "far_above_usual"])


@dataclass
class Signals:
    data_up_to: int
    reference: dict  # country -> reference month
    markets: pd.DataFrame  # market_silence
    medians: pd.DataFrame  # national_medians
    gaps: pd.DataFrame  # series_gaps
    series_last: pd.Series  # series_id -> last usable month
    series_counts: pd.Series  # series_id -> number of usable months


def compute_signals(panel: pd.DataFrame, data_up_to: int) -> Signals:
    reference = reference_months(panel, data_up_to)
    medians = national_medians(panel, data_up_to)
    u = usable(panel, data_up_to)
    return Signals(data_up_to, reference, market_silence(panel, data_up_to, reference), medians,
                   series_gaps(panel, medians, data_up_to), u.groupby("series_id")["m"].max(),
                   u.groupby("series_id")["m"].nunique())


def silent_series(panel: pd.DataFrame, signals: Signals, known: set) -> pd.DataFrame:
    """Series of listed silent markets (fpw.signals.market_silence) that are not in the forecast summary (`known`
    series ids) and have >= MIN_MONTHS months: kept in the export with history only, so a market that goes quiet
    stays visible instead of disappearing. (A single food that WFP stopped collecting in a market that still
    reports is not kept: that is not a market going silent.)"""
    names = panel.sort_values("m").groupby("series_id")[["country", "market_id", "series_commodity_id", "commodity",
                                                          "market", "unit"]].last()
    names = names.assign(m_last=signals.series_last.reindex(names.index),
                         n_months=signals.series_counts.reindex(names.index)).dropna(subset=["m_last"])
    listed = signals.markets.loc[signals.markets["listed"], ["country", "market_id"]]
    in_listed = pd.MultiIndex.from_frame(names[["country", "market_id"]]).isin(pd.MultiIndex.from_frame(listed))
    keep = names[~names.index.isin(known) & in_listed & (names["n_months"] >= MIN_MONTHS)]
    u = usable(panel, signals.data_up_to)
    reported = u[u["m"] > signals.data_up_to - 12].groupby("series_id")["m"].nunique()
    return keep.assign(m_last=keep["m_last"].astype(int),
                       months_reported_12=reported.reindex(keep.index).fillna(0).astype(int)).reset_index()


def pct(log_gap: float) -> int:
    return int(round(100 * (np.exp(log_gap) - 1)))


def signal_facts(gap_row, silence_row, reference: int | None, country: str) -> dict:
    """Facts for one series: gap (or None), silence (or None). Percentages as exported (integers). The gap is
    given only for a current price (its month at most one month before the reference month) and not for a silent
    market: an old gap can be an unconfirmed data error that no later price could reverse."""
    f = {"country": country, "gap": None, "silence": None}
    current = gap_row is not None and (reference is None or int(gap_row["month"]) >= reference - (SILENT_AFTER - 1))
    if current and not (silence_row is not None and silence_row["silent"]):
        f["gap"] = {"month": int(gap_row["month"]), "pct": pct(gap_row["gap"]), "n": int(gap_row["n_markets"]),
                    "usual_pct": pct(gap_row["usual_gap"]) if pd.notna(gap_row["usual_gap"]) else None,
                    "far_above_usual": bool(gap_row["far_above_usual"])}
    if silence_row is not None and silence_row["silent"]:
        f["silence"] = {"months": int(silence_row["months"]), "last_month": int(silence_row["last_month"]),
                        "reference": int(reference)}
    return f


def describe_signals(f: dict, lang: str = "en") -> str:
    from fpw.explain import FLAT_PCT
    from fpw.texts import IN_COUNTRY, MONTHS, SIGNAL_TEXTS
    t, months = SIGNAL_TEXTS[lang], MONTHS[lang]
    month = lambda m: f"{months[m % 12]} {m // 12}"
    side = lambda p: "at" if abs(p) < FLAT_PCT else ("above" if p > 0 else "below")
    parts = []
    if f["gap"] is not None:
        g = f["gap"]
        text = t[f"gap_{side(g['pct'])}"].format(month=month(g["month"]), pct=abs(g["pct"]), n=g["n"])
        if g["usual_pct"] is not None:
            text += t[f"usual_{side(g['usual_pct'])}"].format(pct=abs(g["usual_pct"]))
        parts.append(text + ".")
        if g["far_above_usual"]:
            parts.append(t["far"])
    if f["silence"] is not None:
        s = f["silence"]
        parts.append(t["silent"].format(month=month(s["last_month"]), ref=month(s["reference"]),
                                        in_country=IN_COUNTRY[lang][f["country"]]))
    return " ".join(parts)
