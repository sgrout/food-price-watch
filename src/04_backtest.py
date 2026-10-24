# Databricks notebook source
# MAGIC %md
# MAGIC # 04 - Backtest all forecasters (walk-forward)
# MAGIC For every origin month since `first_origin_year`: use only data up to origin - 2 months (publication lag), refit
# MAGIC each model, forecast steps 1-5 (1-2 nowcast, 3-5 the next 1-3 calendar months), and score against what was later
# MAGIC observed. Models:
# MAGIC - baselines `naive`, `seasonal_rw`, `alps_ar1` (refit per series and origin);
# MAGIC - `lgbm`: pooled LightGBM quantile model, refit every January on cases published by then (from `first_ml_year`);
# MAGIC - `*_cal`: seasonal_rw and lgbm recalibrated with their own past, published errors (PITs).
# MAGIC
# MAGIC All models are compared on the same cases (`common_rows`). The chosen model follows the fixed rule
# MAGIC (`fpw.backtest.choose_model`: validation mean pinball among `CANDIDATES`).
# MAGIC Writes `fpw_{env}_gold.backtest_forecasts`, `backtest_metrics`, `backtest_metrics_country`,
# MAGIC `spike_calibration` (overwrite) and logs an MLflow run with a nested run per model.

# COMMAND ----------

import time

import mlflow
import pandas as pd

from fpw.backtest import CANDIDATES, LAG, calibration, choose_model, common_rows, score, summarize, walk_forward
from fpw.baselines import MODELS
from fpw.calibrate import MIN_PITS, WINDOW_MONTHS, recalibrate
from fpw.features import FEATURES, build_cases
from fpw.ml import PARAMS, TRAIN_YEARS, lgbm_walk_forward
from fpw.panel import monthly_panel
from fpw.schemas import (BACKTEST_FORECASTS, BACKTEST_METRICS, BACKTEST_METRICS_COUNTRY, SPIKE_CALIBRATION,
                         to_rows)

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("experiment_id", "")
dbutils.widgets.text("first_origin_year", "2008")
dbutils.widgets.text("first_ml_year", "2012")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
experiment_id = dbutils.widgets.get("experiment_id")
first_origin_year = int(dbutils.widgets.get("first_origin_year"))
first_ml_year = int(dbutils.widgets.get("first_ml_year"))

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"
t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:5.0f}s] {msg}")


# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origins = range(first_origin_year * 12, int(panel["m"].max()) + LAG)
baselines = walk_forward(panel, origins)
log(f"baselines: {len(baselines):,} forecasts")
cases = build_cases(panel, origins)
log(f"cases: {len(cases):,} ({int(cases['actual'].notna().sum()):,} observed)")
ml = lgbm_walk_forward(cases, first_test_year=first_ml_year)
log(f"lgbm: {len(ml):,} forecasts")
raw = pd.concat([baselines, ml], ignore_index=True).assign(calibrated=False)
calibrated = recalibrate(raw[raw["model"].isin(["seasonal_rw", "lgbm"])])
log(f"recalibrated: {len(calibrated):,} forecasts ({int(calibrated['calibrated'].sum()):,} with enough past PITs)")

scored = score(common_rows(pd.concat([raw, calibrated], ignore_index=True)))
metrics = summarize(scored)
metrics_country = summarize(scored, by=("model", "split", "country", "step"))
spike_cal = calibration(scored)
chosen = choose_model(metrics, candidates=CANDIDATES)
log(f"{len(scored):,} scored rows in common, {scored['series_id'].nunique():,} series; chosen on validation: {chosen}")

# COMMAND ----------


def write(df: pd.DataFrame, ddl: str, table: str) -> None:
    spark.createDataFrame(to_rows(df, ddl), ddl).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.{table}")


# The forecasts table is large (millions of rows): convert in chunks to keep each Spark Connect request small.
chunk = 250_000
for i, start in enumerate(range(0, len(scored), chunk)):
    part = spark.createDataFrame(to_rows(scored.iloc[start:start + chunk], BACKTEST_FORECASTS), BACKTEST_FORECASTS)
    part.write.mode("overwrite" if i == 0 else "append").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.backtest_forecasts")
write(metrics, BACKTEST_METRICS, "backtest_metrics")
write(metrics_country, BACKTEST_METRICS_COUNTRY, "backtest_metrics_country")
write(spike_cal, SPIKE_CALIBRATION, "spike_calibration")
log("tables written")

# COMMAND ----------

if experiment_id:
    mlflow.set_experiment(experiment_id=experiment_id)

with mlflow.start_run(run_name="backtest"):
    mlflow.log_params({
        "lag_months": LAG, "first_origin_year": first_origin_year, "first_ml_year": first_ml_year,
        "models": ",".join(sorted(scored["model"].unique())), "candidates": ",".join(CANDIDATES),
        "chosen_model": chosen, "selection": "validation mean pinball over steps 1-5",
        "recalibration": f"PIT, {WINDOW_MONTHS} months, >= {MIN_PITS}", "lgbm_train_years": TRAIN_YEARS,
        "lgbm_features": ",".join(FEATURES), **{f"lgbm_{k}": v for k, v in PARAMS.items()},
        "n_series": scored["series_id"].nunique(), "n_rows": len(scored),
    })
    mlflow.log_table(metrics, "metrics.json")
    mlflow.log_table(spike_cal, "spike_calibration.json")
    for model in sorted(scored["model"].unique()):
        with mlflow.start_run(run_name=model, nested=True):
            mlflow.log_param("model", model)
            for _, r in metrics[metrics["model"] == model].iterrows():
                prefix = f"{r['split']}_step{r['step']}"
                mlflow.log_metrics({f"{prefix}_{m}": float(r[m]) for m in
                                    ["pinball", "coverage80", "coverage95", "brier", "onset_brier"]})

# COMMAND ----------

display(spark.sql(f"""
    SELECT model, split, ROUND(AVG(pinball), 4) AS pinball, ROUND(AVG(coverage80), 3) AS coverage80,
           ROUND(AVG(coverage95), 3) AS coverage95, ROUND(AVG(brier), 3) AS brier,
           ROUND(AVG(onset_brier), 3) AS onset_brier, ROUND(AVG(onset_brier_climatology), 3) AS onset_climatology
    FROM {gold}.backtest_metrics GROUP BY ALL ORDER BY split, pinball
"""))
