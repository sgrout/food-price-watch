"""Data quality: hard checks that stop the pipeline, and flags that keep a row but mark it as suspect.

Nothing is "fixed". Flagged rows keep their value; models and coverage skip `is_suspect` rows by default.
"""

from datetime import date

import numpy as np
import pandas as pd

from fpw.silver import KEY, SERIES_KEY

# A one-month move beyond x1.75 (or below /1.75) that fully reverts the next month (within x1.3 of the month
# before) is almost always a data error. Example: Mali maize, Aug 2017, x2.5-3.5 in most markets for one month.
SPIKE_LOG = np.log(1.75)
REVERT_LOG = np.log(1.3)
# A move beyond x5 that does not revert is a break (unit change, redenomination, persistent extra zero).
BREAK_LOG = np.log(5)
MAX_GAP_DAYS = 62  # neighbours further apart than this are not compared

SUSPECT_FLAGS = {"invalid_price", "spike_revert"}


class DataQualityError(Exception):
    pass


def flag_suspects(prices: pd.DataFrame) -> pd.DataFrame:
    """Add `quality_flag` (None or a reason) and `is_suspect` (excluded from models by default).

    Flags: invalid_price (missing or <= 0), spike_revert (jump and full reversal), level_shift (a break),
    unconfirmed_jump (a big move in the latest observation of a series: may be a real spike, kept, not suspect).
    """
    df = prices.copy()
    df["quality_flag"] = pd.Series([None] * len(df), index=df.index, dtype=object)
    valid = df["price"].notna() & (df["price"] > 0)
    df.loc[~valid, "quality_flag"] = "invalid_price"

    v = df.loc[valid, SERIES_KEY + ["date", "price"]].copy()
    v["_t"] = pd.to_datetime(v["date"])
    v["_lp"] = np.log(v["price"].astype(float))
    v = v.sort_values(SERIES_KEY + ["_t"])
    g = v.groupby(SERIES_KEY, sort=False)
    prev_t, next_t = g["_t"].shift(1), g["_t"].shift(-1)
    prev_lp, next_lp = g["_lp"].shift(1), g["_lp"].shift(-1)
    adj_prev = (v["_t"] - prev_t).dt.days <= MAX_GAP_DAYS
    adj_next = (next_t - v["_t"]).dt.days <= MAX_GAP_DAYS
    d_in, d_out, back = v["_lp"] - prev_lp, next_lp - v["_lp"], next_lp - prev_lp

    spike_revert = (adj_prev & adj_next & (d_in.abs() > SPIKE_LOG) & (d_out.abs() > SPIKE_LOG)
                    & (np.sign(d_in) != np.sign(d_out)) & (back.abs() < REVERT_LOG))
    # A break must persist (no reversal next month) and must not be the way back from a spike_revert.
    after_spike = spike_revert.groupby([v[k] for k in SERIES_KEY], sort=False).shift(1, fill_value=False)
    level_shift = (adj_prev & (d_in.abs() > BREAK_LOG) & ~spike_revert & ~after_spike
                   & ~(adj_next & (d_out.abs() > SPIKE_LOG)))
    unconfirmed = adj_prev & next_t.isna() & (d_in.abs() > SPIKE_LOG) & ~level_shift
    flags = np.select([spike_revert, level_shift, unconfirmed], ["spike_revert", "level_shift", "unconfirmed_jump"],
                      default="")
    flags = pd.Series(flags, index=v.index)
    df.loc[flags[flags != ""].index, "quality_flag"] = flags[flags != ""]
    df["is_suspect"] = df["quality_flag"].isin(SUSPECT_FLAGS)
    return df


def check_prices(prices: pd.DataFrame, currencies: dict[str, tuple[str, ...]]) -> None:
    """Raise DataQualityError if silver prices are not fit for downstream use (structure, not single values)."""
    if prices.empty:
        raise DataQualityError("silver prices are empty")
    problems = []
    dups = int(prices.duplicated(KEY).sum())
    if dups:
        problems.append(f"{dups} duplicate keys on {KEY}")
    for country, rows in prices.groupby("country"):
        unexpected = sorted(set(rows["currency"]) - set(currencies.get(country, ())))
        if unexpected:
            problems.append(f"{country}: unexpected currency {unexpected} (expected {currencies.get(country)})")
    missing = sorted(set(currencies) - set(prices["country"]))
    if missing:
        problems.append(f"no prices for {missing}")
    if problems:
        raise DataQualityError("; ".join(problems))


def check_continuations(prices: pd.DataFrame, continuations: dict[tuple[str, int], int],
                        max_level_change: float = 0.25) -> None:
    """Raise DataQualityError if a linked commodity's price level jumps at the switch (wrong link, other unit).

    Compares the median price across markets in the old commodity's last month with the new one's first month.
    A link whose new commodity has no data yet is fine (nothing to compare).
    """
    problems = []
    for (country, old_id), new_id in continuations.items():
        p = prices[(prices["country"] == country) & (prices["pricetype"] == "Retail")]
        old, new = p[p["commodity_id"] == old_id], p[p["commodity_id"] == new_id]
        if old.empty or new.empty:
            continue
        before = old.loc[old["date"] == old["date"].max(), "price"].median()
        after = new.loc[new["date"] == new["date"].min(), "price"].median()
        change = after / before - 1
        if abs(change) > max_level_change:
            problems.append(f"{country} {old_id}->{new_id}: median price changes {change:+.0%} at the switch")
    if problems:
        raise DataQualityError("; ".join(problems))


def check_freshness(fetch_log: pd.DataFrame, latest_data: dict[str, date], countries: list[str], today: date,
                    max_check_age_days: int = 14, max_data_age_days: int = 120) -> None:
    """Raise DataQualityError if a source stays stale: no successful fetch recently, or no recent data month.

    `fetch_log` has columns country, status, _ingested_at; a fetch is successful if status is new or unchanged.
    WFP publishes with a lag of weeks, so the latest data month may be 2-3 months old; 120 days is the alarm.
    """
    ok = fetch_log[fetch_log["status"].isin(["new", "unchanged"])]
    last_ok = pd.to_datetime(ok.groupby("country")["_ingested_at"].max()).dt.date.to_dict()
    problems = []
    for c in countries:
        if c not in last_ok or (today - last_ok[c]).days > max_check_age_days:
            problems.append(f"{c}: no successful fetch in {max_check_age_days} days (last: {last_ok.get(c)})")
        if c not in latest_data or (today - latest_data[c]).days > max_data_age_days:
            problems.append(f"{c}: latest data month {latest_data.get(c)} is older than {max_data_age_days} days")
    if problems:
        raise DataQualityError("; ".join(problems))
