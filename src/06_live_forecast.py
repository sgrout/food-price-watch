# Databricks notebook source
# MAGIC %md
# MAGIC # 06 - Live forecast (weekly)
# MAGIC Forecasts for this month's origin with the `@champion` model, using only data up to origin - 2 months (the
# MAGIC same rule as the backtest, so the published track record describes these forecasts). Recalibrates with past
# MAGIC published errors (backtest + scored live forecasts) and **appends** both the raw (`lgbm`) and the calibrated
# MAGIC (`lgbm_cal`) rows to `fpw_{env}_gold.live_forecasts`: never overwritten, so the track record is honest.
# MAGIC Rebuilds `fpw_{env}_gold.live_summary` (one row per series, with the explanation text) for the app.

# COMMAND ----------

from datetime import datetime, timezone

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from fpw.backtest import FORECAST_COLUMNS, LAG
from fpw.countries import COUNTRIES
from fpw.features import build_cases
from fpw.live import calibration_pool, live_forecasts, summarize_live
from fpw.panel import month_date, month_index, monthly_panel
from fpw.schemas import LIVE_FORECASTS, LIVE_SUMMARY, to_rows

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
champion = MlflowClient(registry_uri="databricks-uc").get_model_version_by_alias(model_name, "champion")
model = mlflow.pyfunc.load_model(f"models:/{model_name}@champion").unwrap_python_model()

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origin = int(month_index([run_at.date()]).iloc[0])
cases = build_cases(panel, [origin])
print(f"origin {month_date(origin):%Y-%m}, data up to {month_date(origin - LAG):%Y-%m}: {cases['series_id'].nunique():,} "
      f"series, champion v{champion.version}")

# COMMAND ----------

backtest = spark.sql(f"SELECT * FROM {gold}.backtest_forecasts WHERE model = 'lgbm' "
                     f"AND target > {origin - LAG - 60} AND target <= {origin - LAG}").toPandas()
backtest = backtest.reindex(columns=FORECAST_COLUMNS + ["pit"])  # tolerate a table written before a new column
scored_live = (spark.table(f"{gold}.live_scores").toPandas().reindex(columns=FORECAST_COLUMNS + ["pit"])
               if spark.catalog.tableExists(f"{gold}.live_scores") else pd.DataFrame())
pool = calibration_pool(backtest, scored_live, origin)
fc = live_forecasts(cases, model, pool).assign(model_version=str(champion.version), run_at=run_at,
                                               data_month=origin - LAG)
cal = fc[fc["model"] == "lgbm_cal"]
print(f"pool {len(pool):,} past PITs; {len(fc):,} rows; calibrated {int(cal['calibrated'].sum()):,} of {len(cal):,}")

spark.createDataFrame(to_rows(fc, LIVE_FORECASTS), LIVE_FORECASTS).write.mode("append").saveAsTable(
    f"{gold}.live_forecasts")

summary = summarize_live(cases, cal, {c: COUNTRIES[c].currencies[0] for c in COUNTRIES}).assign(
    model_version=str(champion.version), run_at=run_at, data_month=origin - LAG)
spark.createDataFrame(to_rows(summary, LIVE_SUMMARY), LIVE_SUMMARY).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.live_summary")

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, status, COUNT(*) AS series, ROUND(AVG(next_spike), 3) AS mean_next_spike,
           SUM(CAST(eligible_at_origin AS INT)) AS eligible
    FROM {gold}.live_summary GROUP BY ALL ORDER BY country, status
"""))
