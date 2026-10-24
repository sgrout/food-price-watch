# Databricks notebook source
# MAGIC %md
# MAGIC # 00 - Probe: can serverless reach HDX?
# MAGIC A site that works from a laptop may block datacenter IPs, so before building ingestion we check from serverless:
# MAGIC for each country, CKAN `package_show` (metadata, license) and the price CSV download (redirects to S3).
# MAGIC Each payload is validated with `fpw.hdx`. **Writes no tables.** Fails if any country cannot be fetched or parsed.

# COMMAND ----------

import time

from fpw.hdx import HDX_API, check_price_csv, dataset_name, fetch, parse_package, price_resource_url

dbutils.widgets.text("countries", "mali,burkina-faso,burundi")
countries = [c.strip() for c in dbutils.widgets.get("countries").split(",") if c.strip()]

# COMMAND ----------

results, failures = [], []
for country in countries:
    try:
        _, meta_text = fetch(f"{HDX_API}/package_show", params={"id": dataset_name(country)})
        package = parse_package(meta_text)
        csv_url = price_resource_url(package)
        final_url, csv_text = fetch(csv_url)
        rows = check_price_csv(csv_text)
        last_line = csv_text.rstrip().rsplit("\n", 1)[-1]
        results.append((country, package["license_id"], package["metadata_modified"][:10], rows,
                        round(len(csv_text) / 1e6, 1), final_url.split("/")[2], last_line[:10]))
    except Exception as e:  # InvalidPayload, HTTP errors, ...: report every country, then fail once at the end
        failures.append((country, type(e).__name__, str(e)[:200]))
    time.sleep(2)  # be polite to HDX

display(spark.createDataFrame(
    results, "country string, license string, modified string, rows long, mb double, served_by string, last_row string"))

# COMMAND ----------

if failures:
    raise RuntimeError(f"HDX probe failed for {len(failures)} of {len(countries)} countries: {failures}")
print(f"OK: {len(results)} countries reachable and valid from serverless")
