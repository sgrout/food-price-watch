# Databricks notebook source
# MAGIC %md
# MAGIC # 13 - Backtest of the fresher-data candidate (phase 7)
# MAGIC Re-test (owner, 2026-10-29): `lgbm_fresh2` vs the honest reference `lgbm_cal_pub`; see CLAUDE.md.
# MAGIC Fixed before running (CLAUDE.md, phase 7):
# MAGIC - Cases start from the data month WFP had actually published at the official forecast time
# MAGIC   (`fpw.publication.data_months`, from the HDX activity stream, December 2020 on); unknown or earlier: origin - 2.
# MAGIC   Target months stay the same; months already published get no forecast.
# MAGIC - The same pooled LightGBM, features and refits as `lgbm`; recalibration per (country, h = target - data
# MAGIC   month), counting past PITs whose target was published by the origin's data month.
# MAGIC - Compared with the stored `lgbm_cal` rows (`gold.backtest_forecasts`, not changed here) on the cases both have,
# MAGIC   at origins where the calendar is known, population `all`.
# MAGIC - Switch rule (owner's choice: right after the backtest): the candidate replaces `lgbm_cal` only if (vs the reference)
# MAGIC   (1) validation mean pinball < `lgbm_cal` and its 80 % coverage in [0.70, 0.90], and
# MAGIC   (2) holdout (2023+) mean pinball <= `lgbm_cal` and its 80 % coverage in [0.70, 0.90].
# MAGIC
# MAGIC Known optimism: before 2026-10 we know when a country's month first appeared, not when each market's value did;
# MAGIC a first-appearing month is often incomplete. Writes only `gold.fresh_*` tables.

# COMMAND ----------

import time

import pandas as pd

from fpw.backtest import IRREGULAR_BELOW, LAG, common_rows, score, summarize
from fpw.calibrate import recalibrate
from fpw.countries import FORECAST_COUNTRIES
from fpw.features import build_cases
from fpw.ml import lgbm_walk_forward
from fpw.panel import monthly_panel
from fpw.publication import calendar, data_months
from fpw.schemas import BACKTEST_METRICS, BACKTEST_METRICS_COUNTRY, FRESH_DECISION, FRESH_FORECASTS, to_rows

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("first_origin_year", "2008")
dbutils.widgets.text("first_ml_year", "2012")
catalog, env = dbutils.widgets.get("catalog"), dbutils.widgets.get("env")
first_origin_year, first_ml_year = int(dbutils.widgets.get("first_origin_year")), int(dbutils.widgets.get("first_ml_year"))

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze, silver, gold = (f"{catalog}.fpw_{env}_{x}" for x in ("bronze", "silver", "gold"))
t0 = time.time()
log = lambda msg: print(f"[{time.time() - t0:5.0f}s] {msg}")

# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origins = range(first_origin_year * 12, int(panel["m"].max()) + LAG)
cal = calendar(spark.table(f"{bronze}.hdx_activity").select("country", "timestamp", "dataset_end").toPandas())
dm = data_months(cal, FORECAST_COUNTRIES, origins)
known = {k for k, v in dm.items() if v is not None}
log(f"calendar: {len(known):,} known (country, origin) of {len(dm):,}")

MAX_DELAY = 4  # no forecast when the data month is older than origin - 4 (fixed 2026-10-29, re-test)
H_POOL = 5  # calibration groups pool h >= 5 (fixed 2026-10-29, re-test)
dm_pub = {k: (None if v is None else min(v, k[1] - LAG)) for k, v in dm.items()}  # never fresher than origin - 2


def candidate(data_month_map, by, name):
    c = build_cases(panel, origins, data_months=data_month_map)
    c = c[c["m_data"] >= c["origin"] - MAX_DELAY].assign(h_cal=lambda d: d["h"].clip(upper=H_POOL))
    f = lgbm_walk_forward(c, first_test_year=first_ml_year)
    f = f.merge(c[["series_id", "origin", "step", "m_data", "h", "h_cal"]], on=["series_id", "origin", "step"])
    f = recalibrate(f.assign(model=name, calibrated=False), by=("model", "country", by), data_month_col="m_data",
                    suffix="").drop(columns="h_cal")
    log(f"{name}: {len(f):,} forecasts ({int(f['calibrated'].sum()):,} recalibrated)")
    return f


fresh = candidate(dm, "h_cal", "lgbm_fresh2")
reference = candidate(dm_pub, "step", "lgbm_cal_pub")

stored = spark.table(f"{gold}.backtest_forecasts").where("model = 'lgbm_cal'").toPandas()
score_cols = ["split", "in80", "in95", "pinball", "abs_err", "z_actual", "is_spike", "spike_now"]
both = pd.concat([stored.drop(columns=score_cols), fresh.drop(columns=["m_data", "h"]),
                  reference.drop(columns=["m_data", "h"])], ignore_index=True)
both = both[[(c, o) in known for c, o in zip(both["country"], both["origin"])]]
scored = score(common_rows(both))
eligible = scored[scored["eligible_at_origin"]]
populations = {"all": scored, "eligible": eligible}
metrics = pd.concat([summarize(s).assign(population=k) for k, s in populations.items()], ignore_index=True)
metrics_country = pd.concat([summarize(s, by=("model", "split", "country", "step")).assign(population=k)
                             for k, s in populations.items()], ignore_index=True)
log(f"{len(scored):,} scored rows in common")

# COMMAND ----------

m = metrics[metrics["population"] == "all"].groupby(["model", "split"])[["pinball", "coverage80", "n"]] \
    .agg({"pinball": "mean", "coverage80": "mean", "n": "sum"})
rows = []
for rule, split, strict in [("1", "validation", True), ("2", "holdout", False)]:
    cal_p, fr = m.loc[("lgbm_cal_pub", split), "pinball"], m.loc[("lgbm_fresh2", split)]  # re-test
    better = fr["pinball"] < cal_p if strict else fr["pinball"] <= cal_p
    rows.append({"rule": rule, "split": split, "cal_pinball": cal_p, "fresh_pinball": fr["pinball"],
                 "fresh_coverage80": fr["coverage80"], "passed": bool(better and 0.70 <= fr["coverage80"] <= 0.90),
                 "n": int(fr["n"])})
decision = pd.DataFrame(rows)


def write(df, ddl, table):
    spark.createDataFrame(to_rows(df, ddl), ddl).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.{table}")


write(decision, FRESH_DECISION, "fresh_decision")  # small results first: a large write cannot lose them
write(metrics, BACKTEST_METRICS, "fresh_backtest_metrics")
write(metrics_country, BACKTEST_METRICS_COUNTRY, "fresh_backtest_metrics_country")
out = pd.concat([fresh, reference]).merge(scored[scored["model"].isin(["lgbm_fresh2", "lgbm_cal_pub"])][
    ["series_id", "origin", "step", "model", *score_cols]],
                  on=["series_id", "origin", "step", "model"])  # both already have m_data and h
chunk = 250_000
for i, start in enumerate(range(0, len(out), chunk)):
    spark.createDataFrame(to_rows(out.iloc[start:start + chunk], FRESH_FORECASTS), FRESH_FORECASTS).write \
        .mode("overwrite" if i == 0 else "append").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.fresh_backtest_forecasts")
log(f"switch: {bool(decision['passed'].all())}")
display(decision)
