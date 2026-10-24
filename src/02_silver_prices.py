# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Silver: typed prices with version history, quality flags
# MAGIC 1. Every bronze snapshot not yet applied is parsed and compared with what we knew; only new, changed and removed
# MAGIC    keys are appended to `fpw_{env}_silver.wfp_price_versions` (`valid_from` = snapshot time). Re-applying a
# MAGIC    snapshot appends nothing, so reruns are safe.
# MAGIC 2. The current tables are rebuilt from the versions (overwrite): `wfp_prices` (food, with `quality_flag` and
# MAGIC    `is_suspect`) and `exchange_rates` (WFP's exchange-rate "commodities").
# MAGIC 3. Hard quality checks run **before** the overwrite, so bad data never replaces good data.
# MAGIC
# MAGIC Logic: `fpw/silver.py`, `fpw/quality.py` (unit-tested); this notebook only does I/O.

# COMMAND ----------

import pandas as pd

from fpw import InvalidPayload
from fpw.countries import CONTINUATIONS, COUNTRIES
from fpw.quality import check_continuations, check_prices, flag_suspects
from fpw.schemas import EXCHANGE_RATES, PRICE_VERSIONS, PRICES, to_rows
from fpw.silver import current_from_versions, diff_versions, latest_versions, link_continuations, parse_price_csv, \
    split_exchange_rates

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("countries", "mali,burkina-faso,burundi")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
countries = [c.strip() for c in dbutils.widgets.get("countries").split(",") if c.strip()]

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze, silver = f"{catalog}.fpw_{env}_bronze", f"{catalog}.fpw_{env}_silver"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {silver}")
spark.sql(f"CREATE TABLE IF NOT EXISTS {silver}.wfp_price_versions ({PRICE_VERSIONS})")

# COMMAND ----------

# Snapshots newer than the last version applied for their country (a snapshot without changes is re-checked
# next time and again yields nothing).
pending = spark.sql(f"""
    SELECT l.country, l.file_path, l._ingested_at
    FROM {bronze}.hdx_fetch_log l
    LEFT JOIN (SELECT country, max(valid_from) AS applied FROM {silver}.wfp_price_versions GROUP BY country) v
      USING (country)
    WHERE l.status = 'new' AND (v.applied IS NULL OR l._ingested_at > v.applied)
    ORDER BY l._ingested_at
""").collect()
print(f"{len(pending)} snapshot(s) to apply")

versions = spark.table(f"{silver}.wfp_price_versions").toPandas()
appended = []
for snap_row in pending:
    try:
        with open(snap_row["file_path"], encoding="utf-8") as f:
            snapshot = parse_price_csv(f.read(), snap_row["country"])
    except InvalidPayload as e:  # should have been caught in bronze; skip and keep the last good data
        print(f"SKIPPED {snap_row['file_path']}: {e}")
        continue
    new = diff_versions(latest_versions(versions), snapshot, snap_row["_ingested_at"])
    print(f"{snap_row['country']} {snap_row['_ingested_at']}: {len(snapshot):,} rows -> {len(new):,} new versions "
          f"({int(new['is_removed'].sum())} removed)")
    if len(new):
        appended.append(new)
        versions = pd.concat([versions, new], ignore_index=True) if len(versions) else new

if appended:
    new_versions = pd.concat(appended, ignore_index=True)
    spark.createDataFrame(to_rows(new_versions, PRICE_VERSIONS), PRICE_VERSIONS).write.mode("append").saveAsTable(
        f"{silver}.wfp_price_versions")

# COMMAND ----------

current = link_continuations(current_from_versions(versions), CONTINUATIONS)
food, fx = split_exchange_rates(current)
food = flag_suspects(food)

check_prices(food, {c: COUNTRIES[c].currencies for c in countries})
check_continuations(food, CONTINUATIONS)

spark.createDataFrame(to_rows(food, PRICES), PRICES).write.mode("overwrite").option("overwriteSchema", "true") \
    .saveAsTable(f"{silver}.wfp_prices")
spark.createDataFrame(to_rows(fx, EXCHANGE_RATES), EXCHANGE_RATES).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{silver}.exchange_rates")

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, COUNT(*) AS rows, MIN(date) AS first_month, MAX(date) AS last_month,
           SUM(CAST(is_suspect AS INT)) AS suspect, COUNT_IF(quality_flag = 'level_shift') AS breaks,
           COUNT_IF(quality_flag = 'unconfirmed_jump') AS unconfirmed, MAX(last_changed_at) AS last_change_seen
    FROM {silver}.wfp_prices GROUP BY country ORDER BY country
"""))
