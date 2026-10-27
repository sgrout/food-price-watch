"""Monthly panel: one log price per series and month, from silver prices (suspect rows excluded)."""

from datetime import date

import numpy as np
import pandas as pd

from fpw.countries import FORECAST_COUNTRIES, STAPLE_PATTERN
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


def monthly_panel(prices: pd.DataFrame, staples_only: bool = True, countries=FORECAST_COUNTRIES) -> pd.DataFrame:
    """Retail series as (series_id, identity columns, m, lp, suspect_from), invalid prices excluded.

    Only `countries` (default: the forecast countries, fpw.countries.FORECAST_COUNTRIES): a country that is ingested
    but not forecast (Chad) stays out of backtests, models, live forecasts, signals and baskets.

    Suspect values are kept with `suspect_from`, the month in which they are known to be suspect (NaN = never): a
    backtest drops them only from origins at which that month was published (fpw.backtest.history_at), and never
    scores them as targets. `commodity` and `market` are the latest names of a series (a linked commodity keeps its
    newest name). Two observations in one series-month (only across a commodity link) are averaged in log space.
    """
    p = prices[(prices["pricetype"] == "Retail") & (prices["price"] > 0) & prices["country"].isin(countries)]
    if staples_only:
        p = p[p["commodity"].str.contains(STAPLE_PATTERN, case=False, regex=True)]
    suspect_from = np.where(p["is_suspect"], month_index(p["confirmed_date"].where(p["is_suspect"], p["date"])), np.nan)
    p = p.assign(series_id=series_ids(p), m=month_index(p["date"]).to_numpy(), lp=np.log(p["price"].astype(float)),
                 suspect_from=suspect_from)
    names = p.sort_values("m").groupby("series_id")[["country", "market_id", "series_commodity_id", "commodity",
                                                    "market", "unit"]].last()
    out = p.groupby(["series_id", "m"], as_index=False).agg(lp=("lp", "mean"), suspect_from=("suspect_from", "min"))
    out = out.join(names, on="series_id")
    return out[["series_id", "country", "market_id", "series_commodity_id", "commodity", "market", "unit", "m", "lp",
                "suspect_from"]].sort_values(["series_id", "m"])\
        .reset_index(drop=True)
