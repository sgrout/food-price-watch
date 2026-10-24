"""Live forecasts: the registered model, the monthly sanity gate, this month's forecasts and their scoring.

Same rules as the backtest, so the published track record describes what users see: a forecast made in month O
uses data up to O - LAG; recalibration uses past PITs of forecasts whose target was published by O; a target is
scored only once the month after it is published too (so a one-month data error is known and excluded).
"""

import mlflow
import numpy as np
import pandas as pd

from fpw.backtest import FORECAST_COLUMNS, LAG, score, with_pit
from fpw.calibrate import WINDOW_MONTHS, recalibrate
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS
from fpw.features import FEATURES
from fpw.ml import MIN_TRAIN_ROWS, fit_quantile_models, predict_grid, rows_from_grid, training_rows

MODEL_INPUT = FEATURES + ["lp_last"]
GATE_COVERAGE80 = (0.6, 0.95)  # in-sample 80 % coverage outside this range means a broken fit, not a bad model


class QuantileGridModel(mlflow.pyfunc.PythonModel):
    """MLflow pyfunc: input = forecast cases (MODEL_INPUT columns), output = log-price quantile grid g025 ... g975."""

    def __init__(self, models: list, levels=GRID_LEVELS):
        self.models = models
        self.levels = np.asarray(levels)

    def predict(self, context, model_input: pd.DataFrame, params=None) -> pd.DataFrame:
        return pd.DataFrame(predict_grid(self.models, model_input), columns=GRID_COLUMNS, index=model_input.index)


def train_final(cases: pd.DataFrame, refit_month: int) -> tuple[QuantileGridModel, pd.DataFrame]:
    """Fit the production model on cases published by `refit_month` (same purge and window as the backtest)."""
    train = training_rows(cases, refit_month)
    return QuantileGridModel(fit_quantile_models(train)), train


def sanity_gate(model: QuantileGridModel, train: pd.DataFrame) -> tuple[bool, dict]:
    """Checks that a freshly trained model is not broken. Quality is judged by the backtest and the live track
    record; comparing with the champion on recent months would be unfair (the new model was trained on them)."""
    grid = model.predict(None, train[MODEL_INPUT]).to_numpy()
    y = train["actual"].to_numpy()
    cover = float(np.mean((grid[:, GRID_COLUMNS.index("g100")] <= y) & (y <= grid[:, GRID_COLUMNS.index("g900")])))
    checks = {
        "n_train": len(train), "enough_rows": len(train) >= MIN_TRAIN_ROWS,
        "finite": bool(np.isfinite(grid).all()), "monotone": bool((np.diff(grid, axis=1) >= 0).all()),
        "in_sample_coverage80": round(cover, 4),
        "coverage_plausible": GATE_COVERAGE80[0] <= cover <= GATE_COVERAGE80[1],
    }
    ok = all(v for k, v in checks.items() if isinstance(v, bool))
    return ok, checks


def calibration_pool(backtest: pd.DataFrame, scored_live: pd.DataFrame, origin: int, model: str = "lgbm",
                     lag: int = LAG, window: int = WINDOW_MONTHS) -> pd.DataFrame:
    """Past raw forecasts with a PIT that recalibration may use at `origin`: backtest rows plus scored live rows
    (live wins where both exist), target published by origin - lag and within the window."""
    cols = FORECAST_COLUMNS + ["pit"]
    parts = [df.loc[df["model"] == model, cols] for df in (scored_live, backtest) if len(df)]
    if not parts:
        return pd.DataFrame(columns=cols)
    pool = pd.concat(parts, ignore_index=True).drop_duplicates(["series_id", "origin", "step"], keep="first")
    keep = (pool["target"] <= origin - lag) & (pool["target"] > origin - lag - window) & pool["pit"].notna()
    return pool[keep]


def live_forecasts(cases: pd.DataFrame, model: QuantileGridModel, pool: pd.DataFrame) -> pd.DataFrame:
    """Raw ('lgbm') and recalibrated ('lgbm_cal') forecast rows for one origin's cases."""
    origins = cases["origin"].unique()
    if len(origins) != 1:
        raise ValueError(f"live_forecasts expects one origin, got {sorted(origins)}")
    raw = rows_from_grid(cases, model.predict(None, cases[MODEL_INPUT]).to_numpy()).assign(pit=np.nan)
    both = pd.concat([pool.assign(_pool=True), raw.assign(_pool=False)], ignore_index=True)
    cal = recalibrate(both)
    cal = cal[~cal["_pool"].astype(bool)].drop(columns="_pool")
    return pd.concat([raw.assign(calibrated=False), cal], ignore_index=True).drop(columns="pit")


def latest_runs(live: pd.DataFrame) -> pd.DataFrame:
    """The official forecast per origin: the last run in that month (every run is before the outcome is known)."""
    last = live.groupby("origin")["run_at"].transform("max")
    return live[live["run_at"] == last]


def score_live(live: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Score official live forecasts whose target month and the month after it have been published (country level).
    Targets that are known data errors are not scored, as in the backtest."""
    official = latest_runs(live)
    clean = panel[panel["suspect_from"].isna()][["series_id", "m", "lp"]].rename(columns={"m": "target", "lp": "actual"})
    country_last = panel.groupby("country")["m"].max()
    scorable = official[official["target"] + 1 <= official["country"].map(country_last)]
    rows = scorable.drop(columns=["actual"], errors="ignore").merge(clean, on=["series_id", "target"], how="inner")
    if rows.empty:
        return rows
    return score(with_pit(rows))
