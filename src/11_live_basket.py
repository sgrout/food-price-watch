# Databricks notebook source
# MAGIC %md
# MAGIC # 11 - Live basket forecast and scoring (weekly, job `fpw_basket`)
# MAGIC Basket forecasts for this month's origin from the latest live item forecasts (`gold.live_forecasts`, model
# MAGIC `lgbm_cal`, read-only); the copula's past errors come from the item backtest and scored live items. Appends
# MAGIC `basket_copula` (product) and `basket_comonotone` (hidden shadow) to `gold.live_basket_forecasts` (never
# MAGIC overwritten) and rebuilds `gold.live_basket_scores` / `live_basket_metrics`. Reads nothing it writes elsewhere.

# COMMAND ----------

import pandas as pd

from fpw.backtest import LAG, summarize
from fpw.basket import basket_components, basket_cost_history, load_baskets, load_conversions
from fpw.basket_model import basket_items, basket_panel, basket_walk_forward
from fpw.live import calibration_pool, score_live
from fpw.panel import monthly_panel
from fpw.schemas import BACKTEST_METRICS, LIVE_FORECASTS, LIVE_SCORES, to_rows

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
catalog, env = dbutils.widgets.get("catalog"), dbutils.widgets.get("env")
spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"

# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
comps = basket_components(panel, load_baskets(), load_conversions())
hist = basket_cost_history(panel, comps)
series = spark.createDataFrame(comps[["series_id"]].drop_duplicates())
cur = spark.sql(f"""SELECT * FROM {gold}.live_forecasts WHERE model = 'lgbm_cal'
                    AND run_at = (SELECT MAX(run_at) FROM {gold}.live_forecasts)""").join(series, "series_id").toPandas()
origin = int(cur["origin"].iloc[0])
backtest = spark.table(f"{gold}.backtest_forecasts").where(
    f"model = 'lgbm_cal' AND target > {origin - LAG - 60} AND target <= {origin - LAG}").join(series, "series_id").toPandas()
scored_live = (spark.table(f"{gold}.live_scores").where("model = 'lgbm_cal'").join(series, "series_id").toPandas()
               if spark.catalog.tableExists(f"{gold}.live_scores") else pd.DataFrame())
pool = calibration_pool(backtest, scored_live, origin, model="lgbm_cal")
items = basket_items(pd.concat([pool, cur.reindex(columns=pool.columns)], ignore_index=True), comps)
run = {"calibrated": True, "model_version": str(cur["model_version"].iloc[0]), "run_at": cur["run_at"].iloc[0],
       "data_month": origin - LAG}
fc = pd.concat([basket_walk_forward(items, hist, m, only_origins=[origin]) for m in ["copula", "comonotone"]],
               ignore_index=True).drop(columns="pit").assign(**run)
print(f"origin {origin}: {fc['series_id'].nunique()} baskets, {len(fc)} rows")
spark.createDataFrame(to_rows(fc, LIVE_FORECASTS), LIVE_FORECASTS).write.mode("append") \
    .option("mergeSchema", "true").saveAsTable(f"{gold}.live_basket_forecasts")

# COMMAND ----------

live = spark.table(f"{gold}.live_basket_forecasts").toPandas()
scores = score_live(live, basket_panel(hist))
scores = scores.assign(split="live") if len(scores) else scores
spark.createDataFrame(to_rows(scores, LIVE_SCORES) if len(scores) else [], LIVE_SCORES).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.live_basket_scores")
metrics = pd.concat([summarize(scores).assign(population="all"),
                     summarize(scores[scores["eligible_at_origin"]]).assign(population="eligible")],
                    ignore_index=True) if len(scores) else pd.DataFrame()
spark.createDataFrame(to_rows(metrics, BACKTEST_METRICS) if len(metrics) else [], BACKTEST_METRICS) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{gold}.live_basket_metrics")
print(f"{len(scores)} live basket forecasts scored")
