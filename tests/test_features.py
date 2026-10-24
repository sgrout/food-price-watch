import numpy as np
import pandas as pd

from fpw.backtest import LAG
from fpw.features import FEATURES, add_group_features, build_cases, commodity_group
from simulate import panel, random_walk, seasonal_ar1

M0 = 2005 * 12


def test_commodity_groups():
    assert [commodity_group(c) for c in ["Maize flour", "Cassava flour", "Wheat flour", "Rice (local)",
                                         "Beans (haricot, yellow)", "Oil (palm)", "Salt"]] == \
        ["maize", "cassava", "wheat", "rice", "beans", "oil", "other"]


def test_features_do_not_change_when_the_future_changes():
    """No look-ahead: every feature of a case depends only on data up to origin - LAG, also across markets."""
    rng = np.random.default_rng(1)
    series = {f"s{i}": seasonal_ar1(120, 0.08, 0.6, rng) for i in range(3)}
    origin = M0 + 80
    base = build_cases(panel(series), [origin])
    shocked = {k: v.copy() for k, v in series.items()}
    for v in shocked.values():
        v[80 - LAG + 1:] += rng.normal(0, 1, len(v) - (80 - LAG + 1))
    after = build_cases(panel(shocked), [origin])
    cols = [c for c in FEATURES + ["lp_last", "expected", "sigma"]]
    pd.testing.assert_frame_equal(base[cols], after[cols])
    assert not np.allclose(base["actual"], after["actual"])


def test_case_values():
    lp = random_walk(100, 0.05, np.random.default_rng(2))
    origin = M0 + 60
    c = build_cases(panel({"s": lp}), [origin]).iloc[0]
    last = 60 - LAG
    assert c["lp_last"] == lp[last] and c["ret3"] == lp[last] - lp[last - 3]
    assert c["step"] == 1 and c["target"] == origin - LAG + 1 and c["actual"] == lp[last + 1]
    assert c["target_month"] == (origin - LAG + 1) % 12 and c["n_hist"] == last + 1


def test_unobserved_targets_are_kept_as_cases():
    lp = random_walk(62, 0.05, np.random.default_rng(3))
    cases = build_cases(panel({"s": lp}), [M0 + 62 + LAG - 1])  # last usable month = last observation
    assert len(cases) == 5 and cases["actual"].isna().all()


def test_group_features_are_medians_over_series_not_steps():
    cases = pd.DataFrame({
        "series_id": ["a", "a", "b", "c"], "country": ["mali"] * 4, "commodity_group": ["maize"] * 4,
        "origin": [1, 1, 1, 1], "ret1": [0.1, 0.1, 0.3, 0.2], "ret3": [0.0] * 4, "z_now": [1.0, 1.0, 2.0, 3.0],
    })
    g = add_group_features(cases)
    assert (g["grp_ret1"] == 0.2).all() and (g["grp_z"] == 2.0).all() and (g["grp_n"] == 3).all()
