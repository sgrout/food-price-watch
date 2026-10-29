"""When WFP published which data month, per country: the publication calendar (phase 7, fresher data).

The price CSV has no publication date per row and HDX overwrites it, so we read HDX's activity stream
(`package_activity_list`): each change of the dataset carries its `dataset_date` ("[first TO last]"), i.e. the
latest data month published at that moment. Available from about December 2020; from 2026-10-24 our own weekly
snapshots (silver `valid_from`) give the exact answer per row.

Only non-personal fields are kept (no user, creator or maintainer ids): see ACTIVITY_FIELDS.
"""

import json
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from fpw import InvalidPayload

ACTIVITY_FIELDS = ["activity_id", "timestamp", "activity_type", "dataset", "dataset_end", "price_last_modified"]
_END = re.compile(r"TO (\d{4})-(\d{2})-\d{2}")


def month_of(dataset_date: str | None) -> int | None:
    """'[2003-01-15T00:00:00 TO 2026-08-15T23:59:59]' -> month index of 2026-08 (year * 12 + month - 1)."""
    m = _END.search(dataset_date or "")
    return int(m.group(1)) * 12 + int(m.group(2)) - 1 if m else None


def parse_activity_page(text: str) -> list[dict]:
    """The activities of one package_activity_list page (include_data=true), trimmed to ACTIVITY_FIELDS.
    Raises InvalidPayload if the payload is not a successful CKAN response with a list."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidPayload(f"package_activity_list is not JSON: {text[:80]!r}") from e
    if not isinstance(body, dict) or body.get("success") is not True or not isinstance(body.get("result"), list):
        raise InvalidPayload(f"package_activity_list was not successful: {text[:80]!r}")
    out = []
    for a in body["result"]:
        package = ((a.get("data") or {}).get("package") or {})
        prices = [r for r in package.get("resources", []) if str(r.get("name", "")).endswith("Food Prices")]
        out.append({"activity_id": a.get("id"), "timestamp": a.get("timestamp"), "activity_type": a.get("activity_type"),
                    "dataset": package.get("name"), "dataset_end": package.get("dataset_date"),
                    "price_last_modified": prices[0].get("last_modified") if len(prices) == 1 else None})
    if any(not r["activity_id"] or not r["timestamp"] for r in out):
        raise InvalidPayload("package_activity_list: an activity without id or timestamp")
    return out


def calendar(activities: pd.DataFrame) -> pd.DataFrame:
    """(country, published_at, data_month) for activities that carry a data month, sorted per country."""
    a = activities.assign(published_at=pd.to_datetime(activities["timestamp"], format="ISO8601"),
                          data_month=activities["dataset_end"].map(month_of))
    a = a.dropna(subset=["data_month"]).astype({"data_month": int})
    return a[["country", "published_at", "data_month"]].sort_values(["country", "published_at"]).reset_index(drop=True)


def published_month(cal: pd.DataFrame, country: str, at) -> int | None:
    """The latest data month the country's dataset showed at time `at` (the newest activity at or before it), or
    None if the calendar does not reach back that far."""
    c = cal[cal["country"] == country]
    i = int(np.searchsorted(c["published_at"].to_numpy(), np.datetime64(pd.Timestamp(at)), side="right")) - 1
    return None if i < 0 else int(c["data_month"].iloc[i])


def forecast_time(origin: int) -> datetime:
    """When the official forecast for an origin month is made: the last weekly run of that month (Mondays 06:00 UTC,
    fpw_pipeline), the same moment for every backtest origin."""
    y, m = origin // 12, origin % 12 + 1
    last = (datetime(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    return datetime(last.year, last.month, last.day, 6) - timedelta(days=last.weekday())
