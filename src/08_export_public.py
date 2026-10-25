# Databricks notebook source
# MAGIC %md
# MAGIC # 08 - Public export (weekly)
# MAGIC Builds the public export (contract: `docs/export-contract.md`, schemas: `export/schema/`) from the latest live
# MAGIC run and writes it to the volume `fpw_{env}_gold.public_export`:
# MAGIC - `runs/<YYYY-MM-DD>/...` (all files, kept: versioned history) and `runs/<YYYY-MM-DD>.tar.gz`
# MAGIC - `latest.tar.gz` and `latest/manifest.json` (what the public site fetches)
# MAGIC
# MAGIC `status` stays `preview` until the user decides to publish. Writes nothing outside this volume.

# COMMAND ----------

import json
import os
from datetime import datetime, timezone

import pandas as pd

from fpw.export import build_export, to_tarball

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("status", "preview")
catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
status = dbutils.widgets.get("status")

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"
spark.sql(f"CREATE VOLUME IF NOT EXISTS {gold}.public_export COMMENT 'Public export for the static site'")
root = f"/Volumes/{catalog}/fpw_{env}_gold/public_export"

# COMMAND ----------

summary = spark.table(f"{gold}.live_summary").toPandas()
forecasts = spark.sql(f"""
    SELECT * FROM {gold}.live_forecasts
    WHERE model = 'lgbm_cal' AND run_at = (SELECT MAX(run_at) FROM {gold}.live_forecasts)""").toPandas()
prices = spark.sql(f"""
    SELECT p.country, p.market_id, p.series_commodity_id, p.unit, p.date, p.price, p.is_suspect, p.quality_flag,
           p.admin1, p.admin2, p.latitude, p.longitude
    FROM {silver}.wfp_prices p
    JOIN (SELECT DISTINCT country, market_id, series_commodity_id, unit FROM {gold}.live_summary) s
      USING (country, market_id, series_commodity_id, unit)
    WHERE p.pricetype = 'Retail' AND p.price > 0""").toPandas()
metrics = spark.table(f"{gold}.backtest_metrics").toPandas()
metrics_country = spark.table(f"{gold}.backtest_metrics_country").toPandas()
live_metrics = spark.table(f"{gold}.live_metrics").toPandas()

generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
files = build_export(summary, forecasts, prices, metrics, metrics_country, live_metrics, generated_at, status=status)
tar = to_tarball(files)
print(f"{len(files):,} files, {sum(map(len, files.values())) / 1e6:.1f} MB; tar.gz {len(tar) / 1e6:.2f} MB")

# COMMAND ----------


def write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


stamp = generated_at.strftime("%Y-%m-%d")
for path, data in files.items():
    write(f"{root}/runs/{stamp}/{path}", data)
write(f"{root}/runs/{stamp}.tar.gz", tar)
# latest last, so a reader never sees a new manifest with an old tarball
write(f"{root}/latest.tar.gz", tar)
write(f"{root}/latest/manifest.json", files["manifest.json"])
manifest = json.loads(files["manifest.json"])
display(pd.DataFrame([{k: manifest[k] for k in ["status", "generated_at", "forecast_origin", "data_up_to",
                                                "model_version"]} | manifest["counts"]]))
