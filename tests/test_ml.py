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


def test_adding_countries_does_not_change_an_existing_models_predictions(monkeypatch):
    """fpw.ml codes countries as sorted(COUNTRIES), so a new country shifts the codes; LightGBM re-applies the
    training categories by value at predict time, so a model trained before keeps reading Mali as Mali."""
    import fpw.ml as ml
    from fpw.ml import fit_quantile_models, predict_grid
    rng = np.random.default_rng(3)
    series = {f"s{i}": seasonal_ar1(100, 0.05, 0.5, rng) for i in range(24)}
    p = panel(series)
    p["country"] = np.where(p["series_id"].str[1:].astype(int) % 2 == 0, "mali", "burundi")
    cases = build_cases(p, range(M0 + 48, M0 + 100))
    train = cases[cases["actual"].notna()]
    monkeypatch.setitem(ml._CATEGORIES, "country", ["burkina-faso", "burundi", "mali"])
    models = fit_quantile_models(train, levels=[0.1, 0.5, 0.9], params=FAST)
    before = predict_grid(models, cases)
    monkeypatch.setitem(ml._CATEGORIES, "country", ["burkina-faso", "burundi", "chad", "mali", "niger"])
    np.testing.assert_array_equal(predict_grid(models, cases), before)
