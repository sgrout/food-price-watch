# Databricks notebook source
# MAGIC %md
# MAGIC # 06 - Live forecast (weekly)
# MAGIC Forecasts for this month's origin with two `@champion` models, each under its own backtest's data rule, so the
# MAGIC track record describes these forecasts: the product `lgbm_fresh2` (`lgbm_quantile_fresh`: each country's newest
# MAGIC published month, not older than origin - 4) and `lgbm_cal` (`lgbm_quantile`: origin - 2; the baskets read it).
# MAGIC Recalibrates with past published errors (backtest + scored live forecasts) and **appends** raw and calibrated
# MAGIC rows to `fpw_{env}_gold.live_forecasts`: never overwritten, so the track record is honest.
# MAGIC Rebuilds `fpw_{env}_gold.live_summary` (one row per series of the product, with the explanation text).

# COMMAND ----------

from datetime import datetime, timezone

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from fpw.backtest import FORECAST_COLUMNS, LAG
from fpw.countries import COUNTRIES
from fpw.features import build_cases
from fpw.live import calibration_pool, fresh_live_forecasts, live_forecasts, summarize_live
from fpw.panel import month_date, month_index, monthly_panel
from fpw.publication import FRESH_MODEL, FRESH_RAW, latest_data_months, within_delay
from fpw.schemas import LIVE_FORECASTS, LIVE_SUMMARY, to_rows
from fpw.signals import reference_months

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"
model_name = f"{catalog}.fpw_{env}_ml.lgbm_quantile"
spark.sql(f"CREATE TABLE IF NOT EXISTS {gold}.live_forecasts ({LIVE_FORECASTS})")
run_at = datetime.now(timezone.utc).replace(tzinfo=None)

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")
client = MlflowClient(registry_uri="databricks-uc")
panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origin = int(month_index([run_at.date()]).iloc[0])
scored_live = (spark.table(f"{gold}.live_scores").toPandas()
               if spark.catalog.tableExists(f"{gold}.live_scores") else pd.DataFrame())


def champion(name):
    version = client.get_model_version_by_alias(name, "champion").version
    return str(version), mlflow.pyfunc.load_model(f"models:/{name}@champion").unwrap_python_model()


# COMMAND ----------
# The current model, lgbm_cal: data up to origin - 2. Kept running because the baskets read its live rows.

version, model = champion(model_name)
cases_cal = build_cases(panel, [origin])
backtest = spark.sql(f"SELECT * FROM {gold}.backtest_forecasts WHERE model = 'lgbm' "
                     f"AND target > {origin - LAG - 60} AND target <= {origin - LAG}").toPandas()
backtest = backtest.reindex(columns=FORECAST_COLUMNS + ["pit"])  # tolerate a table written before a new column
scored = scored_live.reindex(columns=FORECAST_COLUMNS + ["pit"]) if len(scored_live) else scored_live
fc_cal = live_forecasts(cases_cal, model, calibration_pool(backtest, scored, origin)).assign(
    model_version=version, run_at=run_at, data_month=origin - LAG)

# COMMAND ----------
# The product, lgbm_fresh2 (phase 7): each country's newest published month; none older than origin - 4.

version, model = champion(f"{model_name}_fresh")
dm = latest_data_months(panel, origin)
cases = within_delay(build_cases(panel, [origin], data_months=dm))
reference = reference_months(panel, origin - 1)  # the month most of a country's markets reported: for the old-price note
cases = cases.assign(reference_month=cases["country"].map(reference))
print(f"origin {month_date(origin):%Y-%m}, data months {({c: f'{month_date(m):%Y-%m}' for (c, _), m in dm.items()})}: "
      f"{cases['series_id'].nunique():,} series, champion v{version}")
past = spark.sql(f"SELECT * FROM {gold}.fresh_raw_forecasts WHERE target > {origin - 1 - 60} AND target < {origin}").toPandas()
scored = scored_live.assign(m_data=scored_live["data_month"]) if len(scored_live) else scored_live
pool = calibration_pool(past, scored, origin, model=FRESH_RAW, lag=1, extra=["m_data"])
fc = fresh_live_forecasts(cases, model, pool).assign(model_version=version, run_at=run_at)
fc = fc.rename(columns={"m_data": "data_month"})
cal = fc[fc["model"] == FRESH_MODEL]
print(f"pool {len(pool):,} past PITs; {len(fc):,} rows; calibrated {int(cal['calibrated'].sum()):,} of {len(cal):,}")

# Both in one run; mergeSchema: new columns are added to the append-only table, old rows keep NULL there
rows = pd.concat([fc_cal, fc], ignore_index=True)
spark.createDataFrame(to_rows(rows, LIVE_FORECASTS), LIVE_FORECASTS).write.mode("append") \
    .option("mergeSchema", "true").saveAsTable(f"{gold}.live_forecasts")

data_month = {c: m for (c, _), m in dm.items()}
summary = summarize_live(cases, cal, {c: COUNTRIES[c].currencies[0] for c in COUNTRIES})
summary = summary.assign(model_version=version, run_at=run_at, data_month=summary["country"].map(data_month))
spark.createDataFrame(to_rows(summary, LIVE_SUMMARY), LIVE_SUMMARY).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.live_summary")

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, status, COUNT(*) AS series, ROUND(AVG(next_spike), 3) AS mean_next_spike,
           SUM(CAST(eligible_at_origin AS INT)) AS eligible
    FROM {gold}.live_summary GROUP BY ALL ORDER BY country, status
"""))
