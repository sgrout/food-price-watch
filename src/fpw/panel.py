"""Monthly panel: one log price per series and month, from silver prices (suspect rows excluded)."""

from datetime import date

import numpy as np
import pandas as pd

from fpw.countries import STAPLE_PATTERN
from fpw.silver import SERIES_KEY


def month_index(dates) -> pd.Series:
    """Months since year 0 (Jan = 0 in `m % 12`), so month arithmetic is integer arithmetic."""
    t = pd.to_datetime(pd.Series(dates))
    return (t.dt.year * 12 + t.dt.month - 1).astype(int)


def month_date(m: int) -> date:
    """Inverse of month_index, on the 15th as in the WFP data."""
    return date(int(m) // 12, int(m) % 12 + 1, 15)


def series_ids(df: pd.DataFrame) -> pd.Series:
    return df[SERIES_KEY].astype(str).agg("|".join, axis=1)


def monthly_panel(prices: pd.DataFrame, staples_only: bool = True) -> pd.DataFrame:
    """Retail series as (series_id, country, commodity, market, m, lp), suspect rows and invalid prices excluded.

    `commodity` and `market` are the latest names of a series (a linked commodity keeps its newest name). Two
    observations in one series-month (only possible across a commodity link) are averaged in log space.
    """
    p = prices[~prices["is_suspect"] & (prices["pricetype"] == "Retail") & (prices["price"] > 0)]
    if staples_only:
        p = p[p["commodity"].str.contains(STAPLE_PATTERN, case=False, regex=True)]
    p = p.assign(series_id=series_ids(p), m=month_index(p["date"]).to_numpy(), lp=np.log(p["price"].astype(float)))
    names = p.sort_values("m").groupby("series_id")[["country", "commodity", "market", "unit"]].last()
    out = p.groupby(["series_id", "m"], as_index=False)["lp"].mean().join(names, on="series_id")
    return out[["series_id", "country", "commodity", "market", "unit", "m", "lp"]].sort_values(["series_id", "m"])\
        .reset_index(drop=True)
