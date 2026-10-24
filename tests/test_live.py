import numpy as np
import pandas as pd
import pytest

from fpw.backtest import LAG
from fpw.distribution import GRID_COLUMNS
from fpw.features import build_cases
from fpw.live import (MODEL_INPUT, QuantileGridModel, calibration_pool, latest_runs, live_forecasts, sanity_gate,
                      score_live, train_final)
from fpw.ml import PARAMS, fit_quantile_models, predict_grid, training_rows
from simulate import panel, seasonal_ar1

M0 = 2005 * 12
FAST = {**PARAMS, "n_estimators": 40, "min_child_samples": 50}


@pytest.fixture(scope="module")
def world():
    rng = np.random.default_rng(3)
    p = panel({f"s{i}": seasonal_ar1(150, 0.05, 0.5, rng) for i in range(30)})
    p["country"] = "mali"
    p["suspect_from"] = np.nan
    origin = int(p["m"].max()) + LAG  # now: last usable month = last observation
    cases = build_cases(p, range(M0 + 48, origin + 1))
    train = training_rows(cases, origin)
    model = QuantileGridModel(fit_quantile_models(train, params=FAST))
    return p, cases, origin, model, train


def test_pyfunc_predicts_the_same_grid_as_the_models(world):
    _, cases, origin, model, _ = world
    now = cases[cases["origin"] == origin]
    out = model.predict(None, now[MODEL_INPUT])
    assert list(out.columns) == GRID_COLUMNS and len(out) == len(now)
    assert np.allclose(out.to_numpy(), predict_grid(model.models, now))


def test_pyfunc_survives_mlflow_save_and_load(world, tmp_path):
    import mlflow
    _, cases, origin, model, _ = world
    now = cases[cases["origin"] == origin]
    import fpw, os
    mlflow.pyfunc.save_model(str(tmp_path / "m"), python_model=model, code_paths=[os.path.dirname(fpw.__file__)])
    loaded = mlflow.pyfunc.load_model(str(tmp_path / "m"))
    assert np.allclose(loaded.predict(now[MODEL_INPUT]).to_numpy(), model.predict(None, now[MODEL_INPUT]).to_numpy())


def test_sanity_gate(world):
    _, cases, origin, model, train = world
    ok, checks = sanity_gate(model, train)
    assert ok and checks["finite"] and checks["monotone"]
    broken = QuantileGridModel([m for m in model.models])
    broken.models = [model.models[5]] * len(model.models)  # every quantile = the median: zero width
    ok, checks = sanity_gate(broken, train)
    assert not ok and not checks["coverage_plausible"]


def test_train_final_uses_only_published_cases(world):
    _, cases, origin, _, _ = world
    _, train = train_final(cases.assign(), origin)
    assert train["target"].max() <= origin - LAG and train["actual"].notna().all()


def pool_rows(n, target, pit, origin=900, model="lgbm", series="p"):
    from fpw.backtest import FORECAST_COLUMNS
    df = pd.DataFrame({c: [0.0] * n for c in FORECAST_COLUMNS})
    df = df.assign(series_id=[f"{series}{i}" for i in range(n)], country="mali", commodity="Maize", model=model,
                   origin=origin, step=1, target=target, pit=pit)
    return df


def test_calibration_pool_window_publication_and_live_first():
    origin = 1000
    bt = pd.concat([pool_rows(3, origin - LAG, 0.5), pool_rows(2, origin - LAG + 1, 0.5, series="late"),
                    pool_rows(2, origin - LAG - 61, 0.5, series="old"), pool_rows(2, origin - 3, 0.5, model="naive", series="n")])
    live = pool_rows(1, origin - LAG, 0.9)  # same key as bt's p0: live wins
    pool = calibration_pool(bt, live, origin)
    assert sorted(pool["series_id"]) == ["p0", "p1", "p2"]
    assert pool.set_index("series_id").loc["p0", "pit"] == 0.9


def test_live_forecasts_raw_and_calibrated_for_one_origin(world):
    _, cases, origin, model, _ = world
    now = cases[cases["origin"] == origin]
    # pool: everything too narrow before (PITs at the extremes) -> recalibration must widen
    # (>= MIN_PITS = 300 past PITs per model x country x step)
    pool = pool_rows(1500, origin - LAG, np.tile([0.01, 0.99], 750))
    pool["step"] = np.repeat([1, 2, 3, 4, 5], 300)
    out = live_forecasts(now, model, pool)
    raw, cal = out[out["model"] == "lgbm"], out[out["model"] == "lgbm_cal"]
    assert len(raw) == len(now) and len(cal) == len(now) and set(out["origin"]) == {origin}
    assert cal["calibrated"].all() and not raw["calibrated"].any()
    w = lambda df: (df["q90"] - df["q10"]).mean()
    assert w(cal) > w(raw)
    with pytest.raises(ValueError):
        live_forecasts(cases[cases["origin"].isin([origin, origin - 1])], model, pool)


def test_latest_runs_keeps_the_last_run_per_origin():
    live = pd.DataFrame({"origin": [1, 1, 2], "run_at": pd.to_datetime(["2026-10-05", "2026-10-26", "2026-11-02"]),
                         "x": [1, 2, 3]})
    assert list(latest_runs(live)["x"]) == [2, 3]


def test_score_live_waits_for_the_following_month_and_skips_known_errors():
    p = panel({"s": np.log(np.full(10, 100.0))})
    p["suspect_from"] = np.nan
    last = int(p["m"].max())
    p.loc[p["m"] == last - 3, "suspect_from"] = last - 2  # a known data error
    from fpw.backtest import FORECAST_COLUMNS
    targets = [last - 3, last - 2, last - 1, last]
    live = pd.DataFrame({c: [0.0] * 4 for c in FORECAST_COLUMNS}).assign(
        series_id="s", country="sim", model="lgbm_cal", origin=last - 4, step=[1, 2, 3, 4], target=targets,
        run_at=pd.Timestamp("2026-10-26"), expected=np.log(100.0), sigma=0.1)
    live[GRID_COLUMNS] = np.log(100.0) + np.linspace(-0.2, 0.2, len(GRID_COLUMNS))
    live[["q025", "q10", "q50", "q90", "q975"]] = live[["g025", "g100", "g500", "g900", "g975"]].to_numpy()
    s = score_live(live, p)
    # last-3: known error; last: the month after is not published yet -> only last-2 and last-1 are scored
    assert sorted(s["target"]) == [last - 2, last - 1] and s["in80"].all()
