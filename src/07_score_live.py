# Databricks notebook source
# MAGIC %md
# MAGIC # 07 - Score live forecasts (weekly)
# MAGIC The official forecast per origin is the last run in that month. It is scored once its target month **and**
# MAGIC the month after it are published (so a one-month data error is known and not scored, as in the backtest).
# MAGIC Rebuilds `fpw_{env}_gold.live_scores` (per forecast) and `live_metrics` (per model, split = 'live', step,
# MAGIC population). Empty until the first targets mature (about 3 months after the first live forecast).

# COMMAND ----------

import pandas as pd

from fpw.backtest import summarize
from fpw.panel import monthly_panel
from fpw.live import score_live
from fpw.schemas import BACKTEST_METRICS, LIVE_SCORES, to_rows

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"

# COMMAND ----------

live = spark.table(f"{gold}.live_forecasts").toPandas()
panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
scores = score_live(live, panel) if len(live) else pd.DataFrame()
if len(scores):
    scores = scores.assign(split="live")
print(f"{len(live):,} live forecast rows; {len(scores):,} scored")

spark.createDataFrame(to_rows(scores, LIVE_SCORES) if len(scores) else [], LIVE_SCORES).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.live_scores")

if len(scores):
    metrics = pd.concat([summarize(scores).assign(population="all"),
                         summarize(scores[scores["eligible_at_origin"]]).assign(population="eligible")],
                        ignore_index=True)
else:
    metrics = pd.DataFrame()
spark.createDataFrame(to_rows(metrics, BACKTEST_METRICS) if len(metrics) else [], BACKTEST_METRICS) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{gold}.live_metrics")
