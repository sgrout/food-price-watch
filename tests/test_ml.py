import numpy as np
import pandas as pd

from fpw.backtest import LAG, common_rows, score, summarize, walk_forward
from fpw.baselines import naive
from fpw.features import build_cases
from fpw.ml import PARAMS, lgbm_walk_forward, training_rows
from simulate import panel, seasonal_ar1

M0 = 2005 * 12
FAST = {**PARAMS, "n_estimators": 60, "min_child_samples": 50}


def test_training_rows_are_purged():
    """Training rows' outcomes must have been published at the refit month."""
    cases = pd.DataFrame({"target": [90, 108, 109, 110, 111], "actual": [1.0, 1.0, 1.0, np.nan, 1.0]})
    rows = training_rows(cases, refit_month=110, lag=LAG, train_years=1)
    assert list(rows["target"]) == [108]  # 109+ not published by 110 (lag 2), 110 unobserved, 90 too old


def test_pooled_model_learns_the_season_and_beats_a_random_walk():
    rng = np.random.default_rng(1)
    series = {f"s{i}": seasonal_ar1(150, 0.05, 0.5, rng) for i in range(40)}
    p = panel(series)
    p["country"] = "mali"
    origins = range(M0 + 48, M0 + 150 + LAG)
    cases = build_cases(p, origins)
    ml = lgbm_walk_forward(cases, first_test_year=2010, params=FAST)
    base = walk_forward(p, origins, models={"naive": naive})
    assert set(ml["model"]) == {"lgbm"} and ml["origin"].min() >= 2010 * 12
    s = summarize(score(common_rows(pd.concat([ml, base]))),
                  by=("model",)).set_index("model")
    assert s.loc["lgbm", "pinball"] < s.loc["naive", "pinball"]
    assert 0.65 < s.loc["lgbm", "coverage80"] < 0.9
    q = ml[["g025", "g050", "g100", "g500", "g900", "g975"]].to_numpy()
    assert (np.diff(q, axis=1) >= 0).all()  # no crossing quantiles
