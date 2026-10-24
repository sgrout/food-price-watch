"""The frames produced by the logic must fit the table schemas the notebooks write (checked before deploying)."""

from datetime import date, datetime

import pandas as pd
import pytest

from fpw import schemas
from fpw.coverage import country_coverage, series_coverage
from fpw.quality import flag_suspects
from fpw.silver import KEY, current_from_versions, diff_versions, latest_versions, link_continuations
from helpers import months, prices


@pytest.fixture(scope="module")
def pipeline():
    snap = prices(months("2020-01", [100.0] * 70 + [float("nan")])).drop(columns="series_commodity_id")
    for col in ["admin1", "admin2"]:
        snap[col] = "A"
    snap[["latitude", "longitude"]] = 12.6, -8.0
    empty = pd.DataFrame(columns=KEY + ["price", "priceflag", "is_removed", "valid_from"])
    versions = diff_versions(latest_versions(empty), snap, pd.Timestamp("2026-10-24 12:00"))
    current = link_continuations(current_from_versions(versions), {})
    food = flag_suspects(current)
    series = series_coverage(food)
    return {"versions": versions, "current": current, "food": food, "series": series,
            "country": country_coverage(series)}


@pytest.mark.parametrize("frame, ddl", [
    ("versions", schemas.PRICE_VERSIONS), ("current", schemas.EXCHANGE_RATES), ("food", schemas.PRICES),
    ("series", schemas.SERIES_COVERAGE), ("country", schemas.COUNTRY_COVERAGE),
])
def test_frames_have_exactly_the_schema_columns(pipeline, frame, ddl):
    df = pipeline[frame]
    assert sorted(schemas.columns(ddl)) == sorted(df.columns)
    rows = schemas.to_rows(df, ddl)
    assert len(rows) == len(df)


def test_to_rows_converts_to_plain_python_values():
    df = pd.DataFrame({"a": [1, 2], "b": [1.5, float("nan")], "d": [date(2024, 1, 15)] * 2,
                       "t": pd.to_datetime(["2026-10-24 12:00", None]), "f": [None, "x"],
                       "i": pd.array([7, None], dtype="Int64")})
    rows = schemas.to_rows(df, "t TIMESTAMP, a BIGINT, b DOUBLE, d DATE, f STRING, i BIGINT")
    assert rows == [(datetime(2026, 10, 24, 12), 1, 1.5, date(2024, 1, 15), None, 7),
                    (None, 2, None, date(2024, 1, 15), "x", None)]
    assert type(rows[0][1]) is int and type(rows[0][2]) is float


def test_to_rows_reports_missing_columns():
    with pytest.raises(KeyError, match="missing columns"):
        schemas.to_rows(pd.DataFrame({"a": [1]}), "a BIGINT, b STRING")
