"""Pooled LightGBM quantile model: one model per quantile level for all series, predicting the log change from the
last observation to the target month. Settings are fixed up front (no hyperparameter search).

Walk-forward: refit every January R on cases whose target month was published by R (target <= R - LAG; this is the
purge: no training row's outcome lies in the period being forecast), using the last TRAIN_YEARS of such cases.
"""

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from fpw.backtest import FORECAST_COLUMNS, LAG, Q_COLUMNS, with_pit
from fpw.baselines import REPORT_LEVELS
from fpw.countries import COUNTRIES
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS, cdf_at
from fpw.features import CATEGORICAL, FEATURES, GROUPS
from fpw.spike import SPIKE_Z

PARAMS = dict(objective="quantile", learning_rate=0.06, n_estimators=250, num_leaves=31, min_child_samples=200,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
TRAIN_YEARS = 10
MIN_TRAIN_ROWS = 5000
_CATEGORIES = {"country": sorted(COUNTRIES), "commodity_group": GROUPS + ["other"]}
_REPORT_IN_GRID = [int(np.argmin(np.abs(GRID_LEVELS - q))) for q in REPORT_LEVELS]


def design(cases: pd.DataFrame) -> pd.DataFrame:
    X = cases[FEATURES].copy()
    for col in CATEGORICAL:
        X[col] = pd.Categorical(X[col], categories=_CATEGORIES[col])
    return X


def training_rows(cases: pd.DataFrame, refit_month: int, lag: int = LAG, train_years: int = TRAIN_YEARS):
    """Observed cases whose outcome was published at the refit month, from the last `train_years`."""
    t = cases["target"]
    return cases[cases["actual"].notna() & (t <= refit_month - lag) & (t > refit_month - lag - 12 * train_years)]


def fit_quantile_models(train: pd.DataFrame, levels=GRID_LEVELS, params=PARAMS, seed: int = 0) -> list:
    X, y = design(train), train["actual"] - train["lp_last"]
    return [LGBMRegressor(alpha=float(q), random_state=seed, **params).fit(X, y) for q in levels]


def predict_grid(models: list, cases: pd.DataFrame) -> np.ndarray:
    """Quantile grid of the log price (n_cases, n_levels); quantiles sorted so they never cross."""
    X = design(cases)
    change = np.sort(np.column_stack([m.predict(X) for m in models]), axis=1)
    return cases["lp_last"].to_numpy()[:, None] + change


def rows_from_grid(cases: pd.DataFrame, grid: np.ndarray, model: str = "lgbm") -> pd.DataFrame:
    """Forecast rows (backtest.FORECAST_COLUMNS) from cases and their predicted log-price grids; the spike
    probability is P(above the case's ALPS-style threshold) under the grid. Used by the backtest and live."""
    rows = cases.assign(model=model)
    rows[GRID_COLUMNS] = grid
    rows[Q_COLUMNS] = grid[:, _REPORT_IN_GRID]
    threshold = (cases["expected"] + SPIKE_Z * cases["sigma"]).to_numpy()
    rows["spike_prob"] = 1 - cdf_at(grid, GRID_LEVELS, threshold)
    return rows[FORECAST_COLUMNS]


def lgbm_walk_forward(cases: pd.DataFrame, first_test_year: int, params=PARAMS, train_years: int = TRAIN_YEARS,
                      lag: int = LAG, seed: int = 0) -> pd.DataFrame:
    """Forecast rows (same columns as backtest.walk_forward) for every observed case from first_test_year on."""
    observed = cases[cases["actual"].notna()]
    out = []
    for year in range(first_test_year, int(observed["origin"].max()) // 12 + 1):
        refit = year * 12
        test = observed[(observed["origin"] >= refit) & (observed["origin"] < refit + 12)]
        train = training_rows(cases, refit, lag, train_years)
        if test.empty or len(train) < MIN_TRAIN_ROWS:
            continue
        grid = predict_grid(fit_quantile_models(train, params=params, seed=seed), test)
        out.append(rows_from_grid(test, grid))
    if not out:
        return pd.DataFrame(columns=FORECAST_COLUMNS + ["pit"])
    return with_pit(pd.concat(out, ignore_index=True))
