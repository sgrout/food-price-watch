import numpy as np
import pandas as pd
import pytest

from fpw import schemas
from fpw.backtest import LAG, calibration, choose_model, common_rows, score, split_of, summarize, walk_forward
from fpw.baselines import naive
from simulate import panel, random_walk, seasonal_ar1

M0 = 2005 * 12


def origins(n_months, start=48):
    return range(M0 + start, M0 + n_months + LAG)


def test_forecasts_do_not_change_when_the_future_changes():
    """No look-ahead: data after the last usable month (origin - LAG) cannot affect a forecast."""
    rng = np.random.default_rng(1)
    lp = seasonal_ar1(120, 0.08, 0.6, rng)
    origin = M0 + 80
    base = walk_forward(panel({"s": lp}), [origin])
    shocked = lp.copy()
    shocked[80 - LAG + 1:] += rng.normal(0, 1, len(shocked) - (80 - LAG + 1))  # every month after origin - LAG
    after = walk_forward(panel({"s": shocked}), [origin])
    forecast_cols = ["model", "step", "q025", "q10", "q50", "q90", "q975", "spike_prob", "expected", "sigma"]
    pd.testing.assert_frame_equal(base[forecast_cols], after[forecast_cols])
    assert not np.allclose(base["actual"], after["actual"])  # only the outcomes moved


def test_lag_and_steps():
    fc = walk_forward(panel({"s": random_walk(100, 0.05, np.random.default_rng(2))}), [M0 + 60], models={"naive": naive})
    assert list(fc["step"]) == [1, 2, 3, 4, 5]
    assert list(fc["target"] - fc["origin"]) == [-1, 0, 1, 2, 3]  # steps 3-5 = the next 1-3 calendar months
    assert (fc["k"] == fc["step"]).all()  # the last usable month was observed


def test_stale_series_are_skipped_and_gaps_raise_k():
    lp = random_walk(100, 0.05, np.random.default_rng(3))
    p = panel({"s": lp})
    origin = M0 + 60
    one_gap = p[p["m"] != origin - LAG]  # last usable month missing -> forecast from one month earlier
    fc = walk_forward(one_gap, [origin], models={"naive": naive})
    assert (fc["k"] == fc["step"] + 1).all()
    stale = p[(p["m"] < origin - LAG - 2) | (p["m"] > origin - LAG)]  # 3 months without data
    assert walk_forward(stale, [origin], models={"naive": naive}).empty


def test_naive_coverage_on_random_walks_is_nominal():
    """Calibration on a simulated random walk, with a tolerance from the effective sample size."""
    rng = np.random.default_rng(4)
    series = {f"s{i}": random_walk(150, 0.05, rng) for i in range(40)}
    scored = score(walk_forward(panel(series), origins(150), models={"naive": naive}))
    s = summarize(scored, by=("step",))
    for _, r in s.iterrows():
        assert abs(r["coverage80"] - 0.8) < 3 * r["coverage80_se"] + 0.02, r.to_dict()
        assert abs(r["coverage95"] - 0.95) < 3 * r["coverage95_se"] + 0.02, r.to_dict()


def test_spike_probabilities_of_the_true_model_are_calibrated():
    rng = np.random.default_rng(5)
    series = {f"s{i}": seasonal_ar1(160, 0.08, 0.7, rng) for i in range(40)}
    scored = score(walk_forward(panel(series), origins(160, start=60)))
    s = summarize(scored, by=("model",)).set_index("model")
    alps = s.loc["alps_ar1"]
    assert abs(alps["spike_rate"] - scored[scored.model == "alps_ar1"]["spike_prob"].mean()) < 0.03
    assert alps["brier"] < alps["brier_climatology"]  # better than always forecasting the base rate
    assert alps["pinball"] < s.loc["naive", "pinball"]  # the true model beats the random walk
    cal = calibration(scored[scored.model == "alps_ar1"], by=("model",))
    big = cal[cal["n"] >= 200]
    assert (np.abs(big["mean_prob"] - big["observed"]) < 0.08).all(), big


def test_score_and_common_rows():
    fc = pd.DataFrame({
        "series_id": ["s", "s", "t"], "origin": [1, 1, 1], "step": [1, 1, 1], "target": [2022 * 12] * 3,
        "model": ["a", "b", "a"], "q025": [0.0] * 3, "q10": [1.0] * 3, "q50": [2.0] * 3, "q90": [3.0] * 3,
        "q975": [4.0] * 3, "spike_prob": [0.9] * 3, "actual": [2.0, 3.5, 5.0], "expected": [1.0] * 3,
        "sigma": [1.0] * 3, "z_now": [0.0] * 3,
    })
    s = score(fc)
    assert list(s["in80"]) == [True, False, False] and list(s["in95"]) == [True, True, False]
    # actual 2.0 = median: pinball = mean over taus of tau*(y - q) for q below, (1-tau)*(q - y) above
    expected = np.mean([0.025 * 2, 0.1 * 1, 0, 0.1 * 1, 0.025 * 2])
    assert s["pinball"].iloc[0] == pytest.approx(expected)
    assert list(s["is_spike"]) == [True, True, True] and (s["split"] == "validation").all()
    assert set(common_rows(fc)["series_id"]) == {"s"}


def test_onset_metrics_only_use_series_not_in_alert_now():
    fc = pd.DataFrame({
        "series_id": list("abcd"), "origin": [1] * 4, "step": [1] * 4, "target": [2022 * 12] * 4, "model": ["m"] * 4,
        "q025": [0.0] * 4, "q10": [0.0] * 4, "q50": [0.0] * 4, "q90": [0.0] * 4, "q975": [0.0] * 4,
        "spike_prob": [0.9, 0.9, 0.1, 0.8], "actual": [2.0, 2.0, 2.0, 0.0], "expected": [0.0] * 4,
        "sigma": [1.0] * 4, "z_now": [2.0, 0.0, 0.0, 0.0],  # a is in alert now; b, c, d are not
    })
    r = summarize(score(fc), by=("model",)).iloc[0]
    assert r["onset_n"] == 3 and r["onset_rate"] == pytest.approx(2 / 3)  # b and c become spikes, d does not
    assert r["onset_precision"] == pytest.approx(0.5) and r["onset_recall"] == pytest.approx(0.5)  # b hit, d false
    assert r["persistence_recall"] == pytest.approx(1 / 3)


def test_split_of():
    m = pd.Series([2019 * 12 + 11, 2020 * 12, 2022 * 12 + 11, 2023 * 12])
    assert list(split_of(m)) == ["dev", "validation", "validation", "holdout"]


def test_choose_model_uses_validation_mean_pinball():
    summary = pd.DataFrame({"model": ["a", "a", "b", "b", "b"], "split": ["validation"] * 4 + ["holdout"],
                            "step": [1, 2, 1, 2, 1], "pinball": [0.01, 0.05, 0.02, 0.03, 0.0]})
    assert choose_model(summary) == "b"  # mean 0.025 < 0.03; the holdout row does not count


def test_backtest_frames_fit_their_schemas():
    rng = np.random.default_rng(6)
    scored = score(common_rows(walk_forward(panel({"s": seasonal_ar1(120, 0.08, 0.6, rng)}), origins(120))))
    frames = {
        schemas.BACKTEST_FORECASTS: scored,
        schemas.BACKTEST_METRICS: summarize(scored),
        schemas.BACKTEST_METRICS_COUNTRY: summarize(scored, by=("model", "split", "country", "step")),
        schemas.SPIKE_CALIBRATION: calibration(scored),
    }
    for ddl, df in frames.items():
        assert sorted(schemas.columns(ddl)) == sorted(df.columns)
        assert len(schemas.to_rows(df, ddl)) == len(df)
