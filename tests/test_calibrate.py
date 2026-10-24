import numpy as np
import pandas as pd
from scipy.stats import norm

from fpw.backtest import LAG, with_pit
from fpw.calibrate import recalibrate
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS


def forecasts(n_origins=120, n_series=20, true_sd=0.10, model_sd=0.05, bias=0.0, seed=1):
    """Gaussian forecasts with median 0 and sd model_sd, while outcomes have sd true_sd (and an optional bias)."""
    rng = np.random.default_rng(seed)
    rows = []
    for o in range(n_origins):
        for s in range(n_series):
            rows.append({"series_id": f"s{s}", "country": "c", "model": "m", "step": 1, "origin": 1000 + o,
                         "target": 1000 + o - LAG + 1, "actual": rng.normal(bias, true_sd)})
    fc = pd.DataFrame(rows)
    grid = norm.ppf(GRID_LEVELS) * model_sd
    fc[GRID_COLUMNS] = np.tile(grid, (len(fc), 1))
    fc[["q025", "q10", "q50", "q90", "q975"]] = fc[["g025", "g100", "g500", "g900", "g975"]].to_numpy()
    fc["spike_prob"] = 1 - norm.cdf(0.1, 0, model_sd)  # P(> 0.1) under the too-narrow model
    return with_pit(fc)


def coverage80(fc):
    return ((fc["q10"] <= fc["actual"]) & (fc["actual"] <= fc["q90"])).mean()


def test_too_narrow_forecasts_are_widened_to_nominal_coverage():
    fc = forecasts()
    assert coverage80(fc) < 0.5  # sd 0.05 vs 0.10: the raw 80 % interval covers ~47 %
    cal = recalibrate(fc, min_pits=100)
    late = cal[cal["calibrated"]]
    assert abs(coverage80(late) - 0.8) < 0.03
    assert (cal["model"] == "m_cal").all()
    # P(> 0.1) is ~2.3 % under the narrow model, ~16 % in truth
    assert abs(late["spike_prob"].mean() - (1 - norm.cdf(0.1, 0, 0.10))) < 0.03


def test_bias_is_corrected():
    cal = recalibrate(forecasts(true_sd=0.05, bias=0.05), min_pits=100)
    late = cal[cal["calibrated"]]
    assert abs((late["q50"] - 0.05).mean()) < 0.01


def test_calibrated_forecasts_stay_almost_unchanged():
    # Single origins move with sampling noise (300 PITs: the 90 % PIT quantile has a standard error of ~0.017 in
    # level; seed 1 happens to start ~3 SE low), so judge the average change.
    # Overlapping 60-month windows carry such a start forward, so average over several seeds.
    changes, covers = [], []
    for seed in range(1, 6):
        fc = forecasts(true_sd=0.05, seed=seed)
        late = recalibrate(fc).query("calibrated")
        raw = fc.set_index(["series_id", "origin"]).loc[late.set_index(["series_id", "origin"]).index]
        changes.append(np.abs(late["q90"].to_numpy() - raw["q90"].to_numpy()).mean())
        covers.append(coverage80(late))
    assert np.mean(changes) < 0.005
    assert abs(np.mean(covers) - 0.8) < 0.02


def test_only_published_outcomes_are_used():
    """No look-ahead: outcomes not yet published at an origin cannot change its recalibrated forecast."""
    fc = forecasts(n_origins=60)
    origin = 1040
    before = recalibrate(fc, min_pits=100).query("origin == @origin")
    shocked = fc.copy()
    unknown = shocked["target"] > origin - LAG
    shocked.loc[unknown, "pit"] = 0.999  # what would happen if later outcomes were all extreme
    after = recalibrate(shocked, min_pits=100).query("origin == @origin")
    pd.testing.assert_frame_equal(before[GRID_COLUMNS + ["spike_prob"]].reset_index(drop=True),
                                  after[GRID_COLUMNS + ["spike_prob"]].reset_index(drop=True))


def test_too_few_past_pits_keeps_the_raw_forecast():
    fc = forecasts(n_origins=10)
    cal = recalibrate(fc, min_pits=10_000)
    assert not cal["calibrated"].any()
    assert np.allclose(cal[GRID_COLUMNS].to_numpy(), fc[GRID_COLUMNS].to_numpy())
