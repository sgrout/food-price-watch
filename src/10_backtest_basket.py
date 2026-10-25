# Databricks notebook source
# MAGIC %md
# MAGIC # 10 - Basket backtest (manual)
# MAGIC Food-basket cost forecasts from the item backtest (`gold.backtest_forecasts`, model `lgbm_cal`, read-only):
# MAGIC `basket_copula` (product candidate), `basket_independence`, `basket_comonotone` (references) and `basket_direct`
# MAGIC (benchmark: seasonal_rw + recalibration on the basket cost series). Rule fixed before the backtest: copula if its
# MAGIC validation 80 % coverage is 0.70-0.90 and its mean pinball is not worse than direct.
# MAGIC Writes only `gold.basket_backtest_forecasts`, `basket_backtest_metrics`, `basket_backtest_metrics_country`.

# COMMAND ----------

import pandas as pd

from fpw.backtest import LAG, common_rows, score, summarize
from fpw.basket import basket_components, basket_cost_history, load_baskets, load_conversions
from fpw.basket_model import basket_items, basket_walk_forward, direct_walk_forward
from fpw.panel import monthly_panel
from fpw.schemas import BACKTEST_FORECASTS, BACKTEST_METRICS, BACKTEST_METRICS_COUNTRY, to_rows

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
item_fc = spark.table(f"{gold}.backtest_forecasts").where("model = 'lgbm_cal'").join(series, "series_id").toPandas()
items = basket_items(item_fc, comps)
print(f"{comps['market_id'].nunique()} markets with a basket; {items['basket_series_id'].nunique()} with item forecasts")

forecasts = [basket_walk_forward(items, hist, m) for m in ["copula", "independence", "comonotone"]]
forecasts.append(direct_walk_forward(hist, range(2008 * 12, int(panel["m"].max()) + LAG)).drop(columns="calibrated"))
allf = pd.concat(forecasts, ignore_index=True).assign(calibrated=True)
scored = score(common_rows(allf[allf["actual"].notna()]))

pops = {"all": scored, "eligible": scored[scored["eligible_at_origin"]]}
metrics = pd.concat([summarize(s).assign(population=k) for k, s in pops.items()], ignore_index=True)
metrics_country = pd.concat([summarize(s, by=("model", "split", "country", "step")).assign(population=k)
                             for k, s in pops.items()], ignore_index=True)
v = metrics[(metrics["population"] == "all") & (metrics["split"] == "validation")].groupby("model")[["coverage80", "pinball"]].mean()
copula_ok = 0.70 <= v.loc["basket_copula", "coverage80"] <= 0.90 and v.loc["basket_copula", "pinball"] <= v.loc["basket_direct", "pinball"]
print(v.round(4).to_string(), "\nchosen:", "basket_copula" if copula_ok else "basket_direct")

# COMMAND ----------

def write(df, ddl, table):
    spark.createDataFrame(to_rows(df, ddl), ddl).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{gold}.{table}")


write(scored, BACKTEST_FORECASTS, "basket_backtest_forecasts")
write(metrics, BACKTEST_METRICS, "basket_backtest_metrics")
write(metrics_country, BACKTEST_METRICS_COUNTRY, "basket_backtest_metrics_country")
display(spark.sql(f"""SELECT population, split, model, ROUND(AVG(coverage80), 3) c80, ROUND(AVG(pinball), 4) pinball
                      FROM {gold}.basket_backtest_metrics GROUP BY ALL ORDER BY population, split, pinball"""))
