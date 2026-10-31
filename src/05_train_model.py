# Databricks notebook source
# MAGIC %md
# MAGIC # 05 - Train the production models and register them (monthly)
# MAGIC Two models: the product `lgbm_quantile_fresh` (cases start from the month published at their forecast time, as in
# MAGIC `13_backtest_fresh`) and `lgbm_quantile` (origin - 2; still read by the baskets).
# MAGIC Fits the pooled LightGBM quantile model (11 quantiles) on all forecast cases whose outcome was published by
# MAGIC this month (same purge and 10-year window as the backtest), wraps it as an MLflow pyfunc and registers it in
# MAGIC Unity Catalog as `{catalog}.fpw_{env}_ml.lgbm_quantile`.
# MAGIC
# MAGIC Aliases: every new version gets `@challenger`; it becomes `@champion` only if the **sanity gate** passes
# MAGIC (finite, non-crossing quantiles, plausible in-sample coverage, enough rows). Which *kind* of model to use was
# MAGIC decided by the backtest; how good it is live is judged by the live track record. The run fails (and emails)
# MAGIC if the gate fails, after registering the version for inspection.

# COMMAND ----------

import os
from datetime import date

import mlflow
from mlflow.tracking import MlflowClient

import fpw
from fpw.backtest import LAG
from fpw.countries import FORECAST_COUNTRIES
from fpw.features import FEATURES, build_cases
from fpw.live import MODEL_INPUT, sanity_gate, train_final
from fpw.ml import PARAMS, TRAIN_YEARS
from fpw.panel import month_date, month_index, monthly_panel
from fpw.publication import calendar, data_months, latest_data_months, within_delay

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("experiment_id", "")

catalog = dbutils.widgets.get("catalog")
env = dbutils.widgets.get("env")
experiment_id = dbutils.widgets.get("experiment_id")

spark.conf.set("spark.sql.session.timeZone", "UTC")
bronze, silver, ml_schema = f"{catalog}.fpw_{env}_bronze", f"{catalog}.fpw_{env}_silver", f"{catalog}.fpw_{env}_ml"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {ml_schema}")
model_name = f"{ml_schema}.lgbm_quantile"

# COMMAND ----------

panel = monthly_panel(spark.table(f"{silver}.wfp_prices").toPandas())
origin = int(month_index([date.today()]).iloc[0])
# Origins far enough back to cover the training window (targets in the last TRAIN_YEARS published by now).
origins = range(origin - 12 * TRAIN_YEARS - 12, origin + 1)
# The product (phase 7) learns as in its backtest: each case starts from the month published at its forecast time.
cal = calendar(spark.table(f"{bronze}.hdx_activity").select("country", "timestamp", "dataset_end").toPandas())
dm = data_months(cal, FORECAST_COUNTRIES, origins)
dm.update(latest_data_months(panel, origin))
TO_TRAIN = {
    model_name: build_cases(panel, origins),  # lgbm_cal: still read by the baskets
    f"{model_name}_fresh": within_delay(build_cases(panel, origins, data_months=dm)),  # lgbm_fresh2: the product
}

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")
if experiment_id:
    mlflow.set_experiment(experiment_id=experiment_id)
client = MlflowClient(registry_uri="databricks-uc")
failed = {}

for name, cases in TO_TRAIN.items():
    model, train = train_final(cases, origin)
    ok, checks = sanity_gate(model, train)
    print(f"{name}, origin {month_date(origin)}: trained on {len(train):,} cases (targets "
          f"{month_date(train['target'].min())} .. {month_date(train['target'].max())}); "
          f"gate {'OK' if ok else 'FAILED'}: {checks}")
    with mlflow.start_run(run_name=f"train_{name.rsplit('.', 1)[-1]}_{month_date(origin):%Y-%m}"):
        mlflow.log_params({"origin": month_date(origin).isoformat(), "lag_months": LAG, "train_years": TRAIN_YEARS,
                           "features": ",".join(FEATURES), **{f"lgbm_{k}": v for k, v in PARAMS.items()}})
        mlflow.log_metrics({k: float(v) for k, v in checks.items()})
        info = mlflow.pyfunc.log_model(
            artifact_path="model",  # MLflow 2.x on the serverless runtime (3.x calls it name=)
            python_model=model,
            code_paths=[os.path.dirname(fpw.__file__)],  # ship the fpw package with the model
            input_example=train[MODEL_INPUT].head(5),
            pip_requirements=["lightgbm==4.7.0", "scikit-learn", "scipy", "pandas", "numpy"],
            registered_model_name=name,
        )
    version = info.registered_model_version
    for key, value in {"origin": month_date(origin).isoformat(), "n_train": str(len(train)), "gate_ok": str(ok),
                       "in_sample_coverage80": str(checks["in_sample_coverage80"])}.items():
        client.set_model_version_tag(name, version, key, value)
    client.set_registered_model_alias(name, "challenger", version)
    if ok:
        client.set_registered_model_alias(name, "champion", version)
    else:
        failed[name] = checks
    print({"model": name, "version": version, "promoted_to_champion": ok})

if failed:
    raise RuntimeError(f"Sanity gate failed, @champion unchanged: {failed}")
