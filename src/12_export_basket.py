# Databricks notebook source
# MAGIC %md
# MAGIC # 12 - Basket export (weekly, job `fpw_basket`)
# MAGIC Writes the optional basket export to `public_export/baskets/` (own manifest and schemas `basket-1.0`):
# MAGIC `runs/<date>/...`, `runs/<date>.tar.gz`, `latest.tar.gz`, `latest/manifest.json`. The item export is untouched.

# COMMAND ----------

import os
from datetime import datetime, timezone

from fpw.basket import basket_components, basket_cost_history, basket_id_of, load_baskets, load_conversions
from fpw.basket_export import build_basket_export
from fpw.export import to_tarball
from fpw.panel import monthly_panel

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("export_status", "beta")
catalog, env, status = (dbutils.widgets.get(k) for k in ("catalog", "env", "export_status"))
spark.conf.set("spark.sql.session.timeZone", "UTC")
silver, gold = f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_gold"
root = f"/Volumes/{catalog}/fpw_{env}_gold/public_export/baskets"

# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
comps = basket_components(panel, load_baskets(), load_conversions())
comps["basket_series_id"] = [basket_id_of(c, m, b) for c, m, b in zip(comps["country"], comps["market_id"], comps["basket_id"])]
hist = basket_cost_history(panel, comps)
item_series = set(spark.table(f"{gold}.live_summary").select("series_id").toPandas()["series_id"])  # as 08_export_public
fc = spark.sql(f"""SELECT * FROM {gold}.live_basket_forecasts WHERE model = 'basket_copula'
                   AND run_at = (SELECT MAX(run_at) FROM {gold}.live_basket_forecasts)""").toPandas()
metrics = spark.table(f"{gold}.basket_backtest_metrics").toPandas()
metrics_country = spark.table(f"{gold}.basket_backtest_metrics_country").toPandas()
live_metrics = spark.table(f"{gold}.live_basket_metrics").toPandas()
generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
files = build_basket_export(comps, hist, fc, metrics, metrics_country, live_metrics, generated_at, status=status,
                            item_series=item_series)
tar = to_tarball(files)
print(f"{len(files)} files, {sum(map(len, files.values())) / 1e6:.1f} MB; tar.gz {len(tar) / 1e6:.2f} MB")


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


stamp = generated_at.strftime("%Y-%m-%d")
for path, data in files.items():
    write(f"{root}/runs/{stamp}/{path}", data)
write(f"{root}/runs/{stamp}.tar.gz", tar)
write(f"{root}/latest.tar.gz", tar)  # latest last
write(f"{root}/latest/manifest.json", files["manifest.json"])
