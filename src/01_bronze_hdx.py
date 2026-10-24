# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Bronze: snapshot WFP price files from HDX
# MAGIC For each country: read the HDX metadata; download the price CSV only if HDX reports a change; store the file
# MAGIC **exactly as received** in the volume `fpw_{env}_bronze.raw`; log every attempt in `fpw_{env}_bronze.hdx_fetch_log`
# MAGIC (status `new`, `unchanged`, `invalid` or `error`). Append-only.
# MAGIC
# MAGIC A failing source does not fail this task: it is logged and skipped, silver keeps the last good data, and the
# MAGIC freshness check at the end of the pipeline fails the run if a source stays stale.

# COMMAND ----------

import os
import time
from datetime import datetime, timezone

from fpw import InvalidPayload
from fpw.bronze import sha256, should_download, snapshot_path
from fpw.hdx import HDX_API, check_price_csv, dataset_name, fetch, parse_package, price_resource
from fpw.schemas import FETCH_LOG, to_rows
import pandas as pd

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("countries", "mali,burkina-faso,burundi")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
countries = [c.strip() for c in dbutils.widgets.get("countries").split(",") if c.strip()]

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze = f"{catalog}.fpw_{env}_bronze"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {bronze}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {bronze}.raw COMMENT 'HDX downloads exactly as received'")
spark.sql(f"CREATE TABLE IF NOT EXISTS {bronze}.hdx_fetch_log ({FETCH_LOG})")
volume_dir = f"/Volumes/{catalog}/fpw_{env}_bronze/raw"

# Last known resource timestamp (from any successful check) and last stored content hash, per country.
prev = {
    r["country"]: r
    for r in spark.sql(f"""
        SELECT country,
               max_by(resource_last_modified, _ingested_at) FILTER (WHERE status IN ('new', 'unchanged')) AS last_modified,
               max_by(sha256, _ingested_at) FILTER (WHERE status = 'new') AS sha256
        FROM {bronze}.hdx_fetch_log GROUP BY country
    """).collect()
}

# COMMAND ----------


def save(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


log = []
for country in countries:
    now = datetime.now(timezone.utc)
    rec = {c: None for c in ["status", "message", "license", "resource_last_modified", "sha256", "n_rows",
                             "file_path", "_source_url"]}
    rec.update(country=country, dataset=dataset_name(country), _source="hdx", _ingested_at=now.replace(tzinfo=None))
    p = prev.get(country)
    try:
        _, meta_text = fetch(f"{HDX_API}/package_show", params={"id": rec["dataset"]})
        package = parse_package(meta_text)
        resource = price_resource(package)
        rec.update(license=package.get("license_id"), resource_last_modified=resource.get("last_modified"),
                   _source_url=resource["url"])
        if not should_download(p["last_modified"] if p else None, rec["resource_last_modified"]):
            rec.update(status="unchanged", message="HDX resource timestamp unchanged; not downloaded")
        else:
            _, text = fetch(resource["url"])
            rec["sha256"] = digest = sha256(text)
            try:
                rec["n_rows"] = check_price_csv(text)
            except InvalidPayload as e:
                rec.update(status="invalid", message=str(e)[:500],
                           file_path=snapshot_path(volume_dir, country, now, digest, invalid=True))
                save(rec["file_path"], text)
            else:
                if p and p["sha256"] == digest:
                    rec.update(status="unchanged", message="new HDX timestamp, same content; not stored")
                else:
                    rec.update(status="new", file_path=snapshot_path(volume_dir, country, now, digest))
                    save(rec["file_path"], text)
    except InvalidPayload as e:
        rec.update(status="invalid", message=str(e)[:500])
    except Exception as e:  # network errors, HTTP 5xx, ...: logged, not raised (see the header)
        rec.update(status="error", message=f"{type(e).__name__}: {e}"[:500])
    print(f"{country}: {rec['status']} {rec['message'] or ''} {rec['n_rows'] or ''}")
    log.append(rec)
    time.sleep(2)  # be polite to HDX

spark.createDataFrame(to_rows(pd.DataFrame(log), FETCH_LOG), FETCH_LOG).write.mode("append").saveAsTable(
    f"{bronze}.hdx_fetch_log")

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, status, message, n_rows, resource_last_modified, file_path, _ingested_at
    FROM {bronze}.hdx_fetch_log ORDER BY _ingested_at DESC LIMIT 20
"""))
