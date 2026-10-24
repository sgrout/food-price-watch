"""Data access for the app: SQL warehouse queries on the gold/silver tables, cached. Read-only."""

import os

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

# Bundle variables are not resolved inside an app's env vars, so catalog and env are plain values (see
# resources/fpw_app.app.yml); FPW_ENV can be overridden for local runs.
CATALOG = os.getenv("FPW_CATALOG", "workspace")
ENV = os.getenv("FPW_ENV", "dev")
GOLD, SILVER = f"{CATALOG}.fpw_{ENV}_gold", f"{CATALOG}.fpw_{ENV}_silver"


@st.cache_resource(ttl=3600)
def _connection():
    cfg = Config()  # the app's service principal (auto-injected credentials)
    return sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
                       credentials_provider=lambda: cfg.authenticate)


def _query(statement: str, params: dict | None = None) -> pd.DataFrame:
    with _connection().cursor() as cursor:
        cursor.execute(statement, params or {})
        return cursor.fetchall_arrow().to_pandas()


@st.cache_data(ttl=900)
def series_list() -> pd.DataFrame:
    return _query(f"SELECT * FROM {GOLD}.live_summary ORDER BY country, commodity, market")


@st.cache_data(ttl=900)
def history(country: str, market_id: int, series_commodity_id: int, unit: str) -> pd.DataFrame:
    return _query(f"""
        SELECT date, price, is_suspect, quality_flag FROM {SILVER}.wfp_prices
        WHERE country = :country AND market_id = :market AND series_commodity_id = :commodity
          AND pricetype = 'Retail' AND unit = :unit AND price > 0
        ORDER BY date""", {"country": country, "market": int(market_id), "commodity": int(series_commodity_id),
                           "unit": unit})


@st.cache_data(ttl=900)
def forecast(series_id: str) -> pd.DataFrame:
    """Calibrated forecast of the latest run for one series."""
    return _query(f"""
        SELECT step, target, q025, q10, q50, q90, q975, spike_prob, expected, sigma, run_at, model_version
        FROM {GOLD}.live_forecasts
        WHERE series_id = :sid AND model = 'lgbm_cal'
          AND run_at = (SELECT MAX(run_at) FROM {GOLD}.live_forecasts WHERE series_id = :sid)
        ORDER BY step""", {"sid": series_id})


@st.cache_data(ttl=3600)
def track_record() -> pd.DataFrame:
    """Backtest metrics for the series that would have been published (population 'eligible')."""
    return _query(f"""
        SELECT model, split, step, n, coverage80, coverage95, pinball, median_abs_err, brier, onset_brier,
               onset_brier_climatology, onset_precision, onset_recall
        FROM {GOLD}.backtest_metrics WHERE population = 'eligible' AND split IN ('validation', 'holdout')""")


@st.cache_data(ttl=3600)
def track_record_country(country: str) -> pd.DataFrame:
    return _query(f"""
        SELECT step, n, coverage80, coverage95, median_abs_err, onset_brier, onset_brier_climatology
        FROM {GOLD}.backtest_metrics_country
        WHERE population = 'eligible' AND split = 'holdout' AND model = 'lgbm_cal' AND country = :country
        ORDER BY step""", {"country": country})


@st.cache_data(ttl=900)
def live_metrics() -> pd.DataFrame:
    return _query(f"SELECT * FROM {GOLD}.live_metrics")
