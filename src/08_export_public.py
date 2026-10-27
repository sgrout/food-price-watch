# Databricks notebook source
# MAGIC %md
# MAGIC # 08 - Public export (weekly)
# MAGIC Builds the public export (contract: `docs/export-contract.md`, schemas: `export/schema/`) from the latest live
# MAGIC run and writes it to the volume `fpw_{env}_gold.public_export`:
# MAGIC - `runs/<YYYY-MM-DD>/...` (all files, kept: versioned history) and `runs/<YYYY-MM-DD>.tar.gz`
# MAGIC - `latest.tar.gz` and `latest/manifest.json` (what the public site fetches)
# MAGIC
# MAGIC `export_status` (job parameter): `preview` (not public), `beta` (public with a beta banner; owner's go 2026-10-25)
# MAGIC or `published`. Writes nothing outside this volume.

# COMMAND ----------

import json
import os
from datetime import datetime, timezone

import pandas as pd

from fpw.export import build_export, to_tarball
from fpw.panel import monthly_panel
from fpw.signals import compute_signals, silent_series

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("export_status", "beta")
dbutils.widgets.text("export_dir", "public_export")  # another volume name = a trial run, not fetched by the site
catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
status = dbutils.widgets.get("export_status")
export_dir = dbutils.widgets.get("export_dir")

spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"
spark.sql(f"CREATE VOLUME IF NOT EXISTS {gold}.{export_dir} COMMENT 'Public export for the static site'")
root = f"/Volumes/{catalog}/fpw_{env}_gold/{export_dir}"

# COMMAND ----------

summary = spark.table(f"{gold}.live_summary").toPandas()
forecasts = spark.sql(f"""
    SELECT * FROM {gold}.live_forecasts
    WHERE model = 'lgbm_cal' AND run_at = (SELECT MAX(run_at) FROM {gold}.live_forecasts)""").toPandas()
# All retail prices: the history of the exported series, and the national medians and silence of every market
prices = spark.sql(f"""
    SELECT country, market_id, market, commodity, series_commodity_id, unit, pricetype, date, price, is_suspect,
           confirmed_date, quality_flag, admin1, admin2, latitude, longitude
    FROM {silver}.wfp_prices
    WHERE pricetype = 'Retail' AND price > 0""").toPandas()
panel = monthly_panel(prices)
signals = compute_signals(panel, int(summary["data_month"].iloc[0]))
silent = silent_series(panel, signals, set(summary["series_id"]))
metrics = spark.table(f"{gold}.backtest_metrics").toPandas()
metrics_country = spark.table(f"{gold}.backtest_metrics_country").toPandas()
live_metrics = spark.table(f"{gold}.live_metrics").toPandas()

generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
files = build_export(summary, forecasts, prices, metrics, metrics_country, live_metrics, generated_at, status=status,
                     signals=signals, silent=silent)
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
