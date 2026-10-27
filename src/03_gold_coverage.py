# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - Gold: data coverage, then the freshness check
# MAGIC `fpw_{env}_gold.series_coverage`: one row per series (food x market x price type x unit) with history,
# MAGIC completeness, recency, flags, and whether it is eligible for a forecast (or the reason why not).
# MAGIC `fpw_{env}_gold.country_coverage`: the summary per country. Both are rebuilt (overwrite) from silver.
# MAGIC
# MAGIC Last cell: **freshness check**. It fails the run (and sends the failure email) when a country had no successful
# MAGIC fetch for 14 days or its latest data month is older than 120 days.

# COMMAND ----------

from datetime import date

from fpw.coverage import country_coverage, series_coverage
from fpw.countries import COUNTRIES
from fpw.quality import check_freshness
from fpw.schemas import COUNTRY_COVERAGE, SERIES_COVERAGE, to_rows

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("countries", "mali,burkina-faso,burundi")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
countries = [c.strip() for c in dbutils.widgets.get("countries").split(",") if c.strip()]

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze, silver, gold = (f"{catalog}.fpw_{env}_{layer}" for layer in ("bronze", "silver", "gold"))
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {gold}")

# COMMAND ----------

prices = spark.table(f"{silver}.wfp_prices").toPandas()
series = series_coverage(prices)
summary = country_coverage(series)

spark.createDataFrame(to_rows(series, SERIES_COVERAGE), SERIES_COVERAGE).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.series_coverage")
spark.createDataFrame(to_rows(summary, COUNTRY_COVERAGE), COUNTRY_COVERAGE).write.mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(f"{gold}.country_coverage")

display(spark.table(f"{gold}.country_coverage"))

# COMMAND ----------

display(spark.sql(f"""
    SELECT country, commodity, COUNT(*) AS eligible_series, ROUND(MEDIAN(n_months) / 12, 1) AS median_years
    FROM {gold}.series_coverage WHERE eligible GROUP BY ALL ORDER BY country, eligible_series DESC
"""))

# COMMAND ----------

fetch_log = spark.sql(f"SELECT country, status, _ingested_at FROM {bronze}.hdx_fetch_log").toPandas()
latest_data = prices.groupby("country")["date"].max().to_dict()
check_freshness(fetch_log, latest_data, countries, today=date.today(),
                data_age_countries=[c for c in countries if COUNTRIES[c].forecast])
print("Freshness OK")
