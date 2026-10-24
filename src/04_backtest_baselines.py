# Databricks notebook source
# MAGIC %md
# MAGIC # 04 - Backtest the baselines (walk-forward)
# MAGIC For every origin month since `first_origin_year`: use only data up to origin - 2 months (publication lag), refit
# MAGIC each baseline per series, forecast steps 1-5 (1-2 nowcast, 3-5 the next 1-3 calendar months), and score against
# MAGIC what was later observed. Models are compared on the same cases only (`common_rows`).
# MAGIC
# MAGIC Writes `fpw_{env}_gold.backtest_forecasts` (scored forecasts), `backtest_metrics` (per model, split, step),
# MAGIC `backtest_metrics_country` and `spike_calibration` (overwrite). Logs one MLflow run with a nested run per model.
# MAGIC The chosen model follows the fixed rule in `fpw.backtest.choose_model` (validation mean pinball loss).

# COMMAND ----------

import mlflow
import pandas as pd

from fpw.backtest import LAG, calibration, choose_model, common_rows, score, summarize, walk_forward
from fpw.baselines import MODELS
from fpw.panel import monthly_panel
from fpw.schemas import (BACKTEST_FORECASTS, BACKTEST_METRICS, BACKTEST_METRICS_COUNTRY, SPIKE_CALIBRATION,
                         to_rows)

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("experiment_id", "")
dbutils.widgets.text("first_origin_year", "2008")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
experiment_id = dbutils.widgets.get("experiment_id")
first_origin_year = int(dbutils.widgets.get("first_origin_year"))

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"

# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origins = range(first_origin_year * 12, int(panel["m"].max()) + LAG)
forecasts = walk_forward(panel, origins)
scored = score(common_rows(forecasts))
print(f"{panel['series_id'].nunique():,} series; {len(forecasts):,} forecasts; {len(scored):,} in common rows "
      f"({scored['series_id'].nunique():,} series)")

metrics = summarize(scored)
metrics_country = summarize(scored, by=("model", "split", "country", "step"))
spike_cal = calibration(scored)
chosen = choose_model(metrics)
print(f"Chosen on validation: {chosen}")

# COMMAND ----------


def write(df: pd.DataFrame, ddl: str, table: str) -> None:
    spark.createDataFrame(to_rows(df, ddl), ddl).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.{table}")


# The forecasts table is large (~1.7 M rows): convert in chunks to keep each Spark Connect request small.
chunk = 250_000
for i, start in enumerate(range(0, len(scored), chunk)):
    part = spark.createDataFrame(to_rows(scored.iloc[start:start + chunk], BACKTEST_FORECASTS), BACKTEST_FORECASTS)
    part.write.mode("overwrite" if i == 0 else "append").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.backtest_forecasts")
write(metrics, BACKTEST_METRICS, "backtest_metrics")
write(metrics_country, BACKTEST_METRICS_COUNTRY, "backtest_metrics_country")
write(spike_cal, SPIKE_CALIBRATION, "spike_calibration")

# COMMAND ----------

if experiment_id:
    mlflow.set_experiment(experiment_id=experiment_id)

with mlflow.start_run(run_name="baseline_backtest"):
    mlflow.log_params({"lag_months": LAG, "first_origin_year": first_origin_year, "models": ",".join(MODELS),
                       "chosen_model": chosen, "selection": "validation mean pinball over steps 1-5",
                       "n_series": scored["series_id"].nunique(), "n_rows": len(scored)})
    mlflow.log_table(metrics, "metrics.json")
    mlflow.log_table(spike_cal, "spike_calibration.json")
    for model in MODELS:
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
