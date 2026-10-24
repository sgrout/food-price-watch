"""Table schemas (Spark DDL) and the pandas -> Spark row conversion used by the notebooks.

Explicit schemas instead of inference: a column that is all None (e.g. no quality flags) cannot be inferred, and
NaN must become NULL, not a floating-point NaN. DDLs are simple `name TYPE` lists (no commas inside types).
"""

import math

import pandas as pd

from fpw.distribution import GRID_COLUMNS

FETCH_LOG = """country STRING, status STRING, message STRING, dataset STRING, license STRING,
    resource_last_modified STRING, sha256 STRING, n_rows BIGINT, file_path STRING,
    _source STRING, _source_url STRING, _ingested_at TIMESTAMP"""

_PRICE_COLUMNS = """country STRING, date DATE, admin1 STRING, admin2 STRING, market STRING, market_id BIGINT,
    latitude DOUBLE, longitude DOUBLE, category STRING, commodity STRING, commodity_id BIGINT, unit STRING,
    priceflag STRING, pricetype STRING, currency STRING, price DOUBLE, usdprice DOUBLE"""

PRICE_VERSIONS = _PRICE_COLUMNS + ", is_removed BOOLEAN, valid_from TIMESTAMP"

EXCHANGE_RATES = _PRICE_COLUMNS + """, series_commodity_id BIGINT, first_seen_at TIMESTAMP,
    last_changed_at TIMESTAMP, n_versions BIGINT"""

PRICES = EXCHANGE_RATES + ", quality_flag STRING, is_suspect BOOLEAN, confirmed_date DATE"

SERIES_COVERAGE = """country STRING, market_id BIGINT, series_commodity_id BIGINT, pricetype STRING, unit STRING,
    market STRING, commodity STRING, category STRING, n_suspect BIGINT, n_breaks BIGINT, first_date DATE,
    last_date DATE, n_months BIGINT, completeness DOUBLE, months_behind DOUBLE, is_staple BOOLEAN, reason STRING,
    eligible BOOLEAN"""

COUNTRY_COVERAGE = """country STRING, markets BIGINT, series BIGINT, retail_staple_series BIGINT,
    eligible_series BIGINT, eligible_markets BIGINT, eligible_commodities BIGINT, median_years_eligible DOUBLE,
    suspect_rows BIGINT, latest_month DATE"""


BACKTEST_FORECASTS = """series_id STRING, country STRING, commodity STRING, market_id BIGINT,
    series_commodity_id BIGINT, unit STRING, origin BIGINT, step BIGINT, target BIGINT,
    k BIGINT, model STRING, q025 DOUBLE, q10 DOUBLE, q50 DOUBLE, q90 DOUBLE, q975 DOUBLE, spike_prob DOUBLE,
    actual DOUBLE, expected DOUBLE, sigma DOUBLE, z_now DOUBLE, split STRING, in80 BOOLEAN, in95 BOOLEAN,
    pinball DOUBLE, abs_err DOUBLE, z_actual DOUBLE, is_spike BOOLEAN, spike_now BOOLEAN, pit DOUBLE, calibrated BOOLEAN, eligible_at_origin BOOLEAN, """ + \
    ", ".join(f"{c} DOUBLE" for c in GRID_COLUMNS)

_METRICS = """n BIGINT, n_series BIGINT, n_origins BIGINT, coverage80 DOUBLE, coverage80_se DOUBLE, coverage95 DOUBLE,
    coverage95_se DOUBLE, pinball DOUBLE, median_abs_err DOUBLE, spike_rate DOUBLE, brier DOUBLE,
    brier_climatology DOUBLE, alert_rate DOUBLE, precision DOUBLE, recall DOUBLE, persistence_precision DOUBLE,
    persistence_recall DOUBLE, onset_n BIGINT, onset_rate DOUBLE, onset_brier DOUBLE, onset_brier_climatology DOUBLE,
    onset_precision DOUBLE, onset_recall DOUBLE"""

BACKTEST_METRICS = "population STRING, model STRING, split STRING, step BIGINT, " + _METRICS
BACKTEST_METRICS_COUNTRY = "population STRING, model STRING, split STRING, country STRING, step BIGINT, " + _METRICS
SPIKE_CALIBRATION = "population STRING, model STRING, split STRING, bin BIGINT, n BIGINT, mean_prob DOUBLE, observed DOUBLE"


def columns(ddl: str) -> list[str]:
    return [part.split()[0] for part in ddl.split(",")]


def _plain(v):
    if v is None or v is pd.NA or v is pd.NaT or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if hasattr(v, "item"):  # numpy scalar -> Python scalar
        return v.item()
    return v


def to_rows(df: pd.DataFrame, ddl: str) -> list[tuple]:
    """Rows in DDL column order with plain Python values (NaN/NA -> None). Raises KeyError on a missing column."""
    cols = columns(ddl)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"missing columns for schema: {missing}")
    return [tuple(_plain(v) for v in row) for row in df[cols].astype(object).itertuples(index=False, name=None)]
