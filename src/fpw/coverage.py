"""Data coverage per series and per country: which series have enough history to get a forecast."""

import pandas as pd

from fpw.countries import STAPLE_PATTERN
from fpw.silver import SERIES_KEY

# Starting rules (revisit in Phase 2 with the backtest): 5 years of usable months, 75 % of months present between
# the first and last observation, and data up to at most 3 months before the country's latest month.
MIN_MONTHS = 60
MIN_COMPLETENESS = 0.75
MAX_MONTHS_BEHIND = 3


def _month_index(dates: pd.Series) -> pd.Series:
    t = pd.to_datetime(dates)
    return t.dt.year * 12 + t.dt.month


def series_coverage(prices: pd.DataFrame) -> pd.DataFrame:
    """One row per series (country, market, commodity, pricetype, unit) with history stats, eligibility and the
    first reason a series is not eligible (`reason`, empty if eligible). Suspect rows do not count as history."""
    p = prices.sort_values("date").assign(_m=_month_index(prices["date"]))
    country_last = p.groupby("country")["_m"].max()
    flags = p.groupby(SERIES_KEY).agg(
        market=("market", "last"), commodity=("commodity", "last"), category=("category", "last"),  # latest names
        n_suspect=("is_suspect", "sum"), n_breaks=("quality_flag", lambda f: int((f == "level_shift").sum())),
    )
    ok = p[~p["is_suspect"]]
    hist = ok.groupby(SERIES_KEY).agg(
        first_date=("date", "min"), last_date=("date", "max"), n_months=("_m", "nunique"),
        _first=("_m", "min"), _last=("_m", "max"),
    )
    s = flags.join(hist, how="left").reset_index()
    s["n_months"] = s["n_months"].fillna(0).astype(int)
    s["completeness"] = (s["n_months"] / (s["_last"] - s["_first"] + 1)).fillna(0).round(3)
    s["months_behind"] = s["country"].map(country_last) - s["_last"]
    s["is_staple"] = s["commodity"].str.contains(STAPLE_PATTERN, case=False, regex=True)

    rules = [
        (~s["is_staple"], "not a staple"),
        (s["pricetype"] != "Retail", "not a retail price"),
        (s["n_months"] < MIN_MONTHS, f"less than {MIN_MONTHS} months of history"),
        (s["completeness"] < MIN_COMPLETENESS, f"less than {MIN_COMPLETENESS:.0%} of months present"),
        (~(s["months_behind"] <= MAX_MONTHS_BEHIND), f"no data in the last {MAX_MONTHS_BEHIND} months"),
    ]
    s["reason"] = ""
    for failed, reason in reversed(rules):  # the first failing rule wins
        s.loc[failed.fillna(True), "reason"] = reason
    s["eligible"] = s["reason"] == ""
    return s.drop(columns=["_first", "_last"])


def country_coverage(series: pd.DataFrame) -> pd.DataFrame:
    """Summary per country: all series vs eligible ones."""
    el = series[series["eligible"]]
    out = pd.DataFrame({
        "markets": series.groupby("country")["market_id"].nunique(),
        "series": series.groupby("country").size(),
        "retail_staple_series": series[series["is_staple"] & (series["pricetype"] == "Retail")].groupby("country").size(),
        "eligible_series": el.groupby("country").size(),
        "eligible_markets": el.groupby("country")["market_id"].nunique(),
        "eligible_commodities": el.groupby("country")["commodity"].nunique(),
        "median_years_eligible": (el.groupby("country")["n_months"].median() / 12).round(1),
        "suspect_rows": series.groupby("country")["n_suspect"].sum(),
        "latest_month": series.groupby("country")["last_date"].max(),
    })
    counts = ["retail_staple_series", "eligible_series", "eligible_markets", "eligible_commodities"]
    out[counts] = out[counts].fillna(0).astype(int)
    return out.reset_index()
