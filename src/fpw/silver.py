"""Silver: typed WFP prices with a version history, so every value is known "as of" the snapshot that first had it.

Versions work like a temporal table: a row is added only when a key is new, its price/priceflag changed, or it
disappeared from the source (a tombstone, `is_removed`). `valid_from` is the bronze snapshot time (`_ingested_at`).
"""

import io

import pandas as pd

from fpw import InvalidPayload
from fpw.hdx import check_price_csv

KEY = ["country", "market_id", "commodity_id", "pricetype", "unit", "date"]
# A series is one food in one market; series_commodity_id links a commodity WFP renamed (see link_continuations).
SERIES_KEY = ["country", "market_id", "series_commodity_id", "pricetype", "unit"]
# A change in these makes a new version. usdprice is left out: it moves whenever WFP updates its FX conversion.
VALUE_COLUMNS = ["price", "priceflag"]


def parse_price_csv(text: str, country: str) -> pd.DataFrame:
    """Raw CSV text -> typed rows. Raises InvalidPayload on a wrong format or unparseable dates/ids.

    Unparseable prices become NaN (flagged in quality, not dropped): one bad cell should not discard a snapshot.
    """
    check_price_csv(text)
    raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    df = pd.DataFrame({
        "country": country,
        "date": pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="coerce").dt.date,
        "admin1": raw["admin1"],
        "admin2": raw["admin2"],
        "market": raw["market"],
        "market_id": pd.to_numeric(raw["market_id"], errors="coerce").astype("Int64"),
        "latitude": pd.to_numeric(raw["latitude"], errors="coerce"),
        "longitude": pd.to_numeric(raw["longitude"], errors="coerce"),
        "category": raw["category"],
        "commodity": raw["commodity"],
        "commodity_id": pd.to_numeric(raw["commodity_id"], errors="coerce").astype("Int64"),
        "unit": raw["unit"],
        "priceflag": raw["priceflag"],
        "pricetype": raw["pricetype"],
        "currency": raw["currency"],
        "price": pd.to_numeric(raw["price"], errors="coerce"),
        "usdprice": pd.to_numeric(raw["usdprice"], errors="coerce"),
    })
    bad = df["date"].isna() | df["market_id"].isna() | df["commodity_id"].isna()
    if bad.any():
        raise InvalidPayload(f"{int(bad.sum())} rows with unparseable date, market_id or commodity_id")
    return df


def latest_versions(versions: pd.DataFrame) -> pd.DataFrame:
    """The most recent version per key (including tombstones)."""
    return versions.sort_values("valid_from", kind="stable").drop_duplicates(KEY, keep="last")


def _same(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a == b) | (a.isna() & b.isna())


def diff_versions(latest: pd.DataFrame, snapshot: pd.DataFrame, ingested_at) -> pd.DataFrame:
    """Version rows to append for one snapshot: new or changed keys, plus tombstones for keys that disappeared.

    `latest` is the output of latest_versions() (may be empty); only the snapshot's countries are compared.
    Applying the same snapshot twice yields no rows the second time (idempotent).
    """
    live = latest[latest["country"].isin(snapshot["country"].unique()) & ~latest["is_removed"].astype(bool)]
    m = snapshot.merge(live[KEY + VALUE_COLUMNS], on=KEY, how="left", suffixes=("", "_old"), indicator=True)
    changed = (m["_merge"] == "left_only").to_numpy()
    for col in VALUE_COLUMNS:
        changed |= ~_same(m[col], m[f"{col}_old"]).to_numpy()
    new = snapshot[changed].assign(is_removed=False)

    gone = live.merge(snapshot[KEY], on=KEY, how="left", indicator=True)
    gone = gone[gone["_merge"] == "left_only"].drop(columns="_merge").assign(is_removed=True)

    out = pd.concat([new, gone[new.columns]], ignore_index=True) if len(gone) else new.reset_index(drop=True)
    return out.assign(valid_from=pd.Timestamp(ingested_at))


def current_from_versions(versions: pd.DataFrame) -> pd.DataFrame:
    """One row per live key: its latest value, when we first saw the key and when its value last changed."""
    first_seen = versions.groupby(KEY)["valid_from"].min().rename("first_seen_at")
    n_versions = versions.groupby(KEY).size().rename("n_versions")
    cur = latest_versions(versions)
    cur = cur[~cur["is_removed"].astype(bool)].rename(columns={"valid_from": "last_changed_at"})
    cur = cur.join(first_seen, on=KEY).join(n_versions, on=KEY).drop(columns="is_removed")
    return cur.sort_values(KEY).reset_index(drop=True)


def as_of(versions: pd.DataFrame, t) -> pd.DataFrame:
    """The data as it was known at time t: the latest version per key with valid_from <= t, minus removed keys."""
    known = latest_versions(versions[versions["valid_from"] <= pd.Timestamp(t)])
    return known[~known["is_removed"].astype(bool)].drop(columns="is_removed").reset_index(drop=True)


def link_continuations(prices: pd.DataFrame, continuations: dict[tuple[str, int], int]) -> pd.DataFrame:
    """Add `series_commodity_id`: the commodity id, or for a re-specified commodity the id it continues as.

    The original commodity_id and name are kept, so the link is visible and can be undone.
    """
    old = list(zip(prices["country"], prices["commodity_id"]))
    series_id = [continuations.get(k, k[1]) for k in old]
    return prices.assign(series_commodity_id=pd.array(series_id, dtype="Int64"))


def split_exchange_rates(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """WFP files include exchange rates as 'commodities' (e.g. 'Exchange rate (unofficial)', unit USD/LCU)."""
    is_fx = prices["commodity"].str.startswith("Exchange rate")
    return prices[~is_fx].reset_index(drop=True), prices[is_fx].reset_index(drop=True)
