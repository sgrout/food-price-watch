import numpy as np
import pytest

from fpw.baselines import LEVELS, MIN_CHANGES, alps_ar1, naive, prob_above, seasonal_rw
from fpw.spike import fit_seasonal_trend
from simulate import SEASON, random_walk

M0 = 2005 * 12


def q_at(q, level):
    return q[..., int(np.argmin(np.abs(LEVELS - level)))]


def test_naive_on_a_random_walk_has_the_right_width():
    arr = random_walk(600, sd=0.05, rng=np.random.default_rng(1))
    q = naive(arr, M0, [1, 4])
    assert np.allclose(q_at(q, 0.5), arr[-1])  # no drift
    width80 = q_at(q, 0.9) - q_at(q, 0.1)
    expected = 2 * 1.2816 * 0.05 * np.sqrt([1, 4])
    assert np.allclose(width80, expected, rtol=0.15)


def test_seasonal_rw_follows_the_season_and_naive_does_not():
    m = M0 + np.arange(72)
    arr = 5 + SEASON[m % 12]  # no noise: next month is exactly the seasonal value
    target = m[-1] + 1
    assert q_at(seasonal_rw(arr, M0, [1]), 0.5)[0] == pytest.approx(5 + SEASON[target % 12])
    assert abs(q_at(naive(arr, M0, [1]), 0.5)[0] - (5 + SEASON[target % 12])) > 0.01


def test_alps_ar1_mean_reverts_to_the_seasonal_norm():
    m = M0 + np.arange(60)
    rng = np.random.default_rng(2)
    lp = 5 + SEASON[m % 12] + rng.normal(0, 0.05, 60)
    lp[-1] += 0.3  # far above the norm now
    fit = fit_seasonal_trend(m, lp)
    q = alps_ar1(lp, M0, [1, 12], fit)
    med = q_at(q, 0.5)
    norm = fit.expected(m[-1] + np.array([1, 12]))
    excess = med - norm
    assert np.allclose(excess, fit.phi ** np.array([1, 12]) * fit.resid_last)
    assert excess[1] <= excess[0]
    # error sd: sigma^2 (1 - phi^2k) + parameter variance
    sd = np.sqrt(fit.sigma ** 2 * (1 - fit.phi ** np.array([2, 24])) + fit.expected_var(m[-1] + np.array([1, 12])))
    assert np.allclose(q_at(q, 0.9) - q_at(q, 0.1), 2 * 1.2816 * sd, rtol=0.01)


def test_not_enough_history_returns_none():
    arr = random_walk(MIN_CHANGES, 0.05, np.random.default_rng(3))  # 23 one-month changes
    assert naive(arr, M0, [1]) is None and seasonal_rw(arr, M0, [1]) is None
    assert alps_ar1(arr, M0, [1], None) is None


def test_quantiles_are_monotone():
    arr = random_walk(200, 0.05, np.random.default_rng(4))
    m = M0 + np.arange(200)
    for q in [naive(arr, M0, [1, 3]), seasonal_rw(arr, M0, [1, 3]), alps_ar1(arr, M0, [1, 3],
                                                                              fit_seasonal_trend(m, arr))]:
        assert (np.diff(q, axis=1) >= 0).all()


def test_prob_above():
    q = np.linspace(-1, 1, len(LEVELS))
    assert prob_above(q, q[np.searchsorted(LEVELS, 0.5)]) == pytest.approx(0.5)
    assert prob_above(q, -5) == pytest.approx(0.995) and prob_above(q, 5) == pytest.approx(0.005)
    assert prob_above(q, 0.2) > prob_above(q, 0.4)
