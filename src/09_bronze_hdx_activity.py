# Databricks notebook source
# MAGIC %md
# MAGIC # 09 - Bronze: HDX activity stream (publication calendar)
# MAGIC When WFP published which data month, per country (phase 7, fresher data): each change of an HDX dataset carries
# MAGIC its `dataset_date` ("[first TO last]"). The first run pages back to about December 2020; later runs only fetch
# MAGIC activities newer than the ones we have. Appends to `fpw_{env}_bronze.hdx_activity` (one row per activity, never
# MAGIC twice) and keeps each trimmed page in the volume (`raw/activity/<country>/`).
# MAGIC
# MAGIC Only non-personal fields are kept (`fpw.publication.ACTIVITY_FIELDS`: no user, creator or maintainer ids).
# MAGIC A failed country is logged and skipped; the task fails at the end so the run notifies.

# COMMAND ----------

import json
import os
import time
from datetime import datetime, timezone

import pandas as pd

from fpw.hdx import HDX_API, dataset_name, fetch
from fpw.publication import parse_activity_page
from fpw.schemas import HDX_ACTIVITY, to_rows

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("countries", "mali,burkina-faso,burundi")
catalog, env = dbutils.widgets.get("catalog"), dbutils.widgets.get("env")
countries = [c.strip() for c in dbutils.widgets.get("countries").split(",") if c.strip()]

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze = f"{catalog}.fpw_{env}_bronze"
spark.sql(f"CREATE TABLE IF NOT EXISTS {bronze}.hdx_activity ({HDX_ACTIVITY})")
volume_dir = f"/Volumes/{catalog}/fpw_{env}_bronze/raw/activity"
known = {r["activity_id"] for r in spark.sql(f"SELECT activity_id FROM {bronze}.hdx_activity").collect()}
PAGE, MAX_PAGES, OLDEST = 100, 20, "2020-11-01"

# COMMAND ----------

new_rows, failures = [], []
for country in countries:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    url = f"{HDX_API}/package_activity_list"
    try:
        for page in range(MAX_PAGES):
            params = {"id": dataset_name(country), "limit": PAGE, "offset": page * PAGE, "include_data": "true"}
            _, text = fetch(url, params=params)
            rows = parse_activity_page(text)
            fresh = [r for r in rows if r["activity_id"] not in known]
            if fresh:
                path = f"{volume_dir}/{country}/{now:%Y-%m-%dT%H%M%S}_{page:02d}.json"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(fresh, f, ensure_ascii=False)
                new_rows += [{**r, "country": country, "_source": "hdx", "_source_url": url, "_ingested_at": now}
                             for r in fresh]
                known |= {r["activity_id"] for r in fresh}
            # stop at the end of the stream, at activities we already have, or before the calendar is useful
            if len(rows) < PAGE or len(fresh) < len(rows) or rows[-1]["timestamp"] < OLDEST:
                break
            time.sleep(2)  # be polite to HDX
        print(f"{country}: {sum(r['country'] == country for r in new_rows)} new activities")
    except Exception as e:  # InvalidPayload, HTTP errors: report, keep the others
        failures.append((country, type(e).__name__, str(e)[:200]))
    time.sleep(2)

if new_rows:
    spark.createDataFrame(to_rows(pd.DataFrame(new_rows), HDX_ACTIVITY), HDX_ACTIVITY).write.mode("append") \
        .saveAsTable(f"{bronze}.hdx_activity")

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, COUNT(*) AS activities, MIN(timestamp) AS first, MAX(timestamp) AS last,
           COUNT(dataset_end) AS with_data_month
    FROM {bronze}.hdx_activity GROUP BY country ORDER BY country"""))
if failures:
    raise RuntimeError(f"HDX activity fetch failed for {len(failures)} of {len(countries)} countries: {failures}")
