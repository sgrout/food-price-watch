import numpy as np

from fpw.spike import MIN_OBS, fit_seasonal_trend
from simulate import SEASON, seasonal_ar1

M0 = 2005 * 12


def test_fit_recovers_season_trend_sigma_and_phi():
    # One persistent series has only ~40 effective observations, so judge the average over many series.
    rng = np.random.default_rng(1)
    m = M0 + np.arange(120)
    fits = [fit_seasonal_trend(m, seasonal_ar1(120, sigma=0.08, phi=0.7, rng=rng, trend=0.01)) for _ in range(100)]
    season = np.mean([f.season - f.season.mean() for f in fits], axis=0)
    assert np.abs(season - SEASON).max() < 0.02
    assert abs(np.mean([f.trend for f in fits]) - 0.01) < 0.001
    # Known downward bias: the trend absorbs part of a persistent residual. Within 15 %.
    assert 0.068 < np.mean([f.sigma for f in fits]) < 0.08
    assert 0.55 < np.mean([f.phi for f in fits]) < 0.7


def test_expected_var_is_larger_further_from_the_data():
    m = M0 + np.arange(60)
    fit = fit_seasonal_trend(m, 5 + SEASON[m % 12] + np.random.default_rng(6).normal(0, 0.05, 60))
    v = fit.expected_var(m[-1] + np.array([1, 12, 60]))
    assert (np.diff(v) > 0).all() and v[0] < fit.sigma ** 2


def test_z_measures_distance_from_the_seasonal_norm():
    m = M0 + np.arange(48)
    lp = 5 + SEASON[m % 12] + np.random.default_rng(2).normal(0, 0.05, 48)
    fit = fit_seasonal_trend(m, lp)
    target = m[-1] + 1
    two_sigma_above = fit.expected(target) + 2 * fit.sigma
    assert np.isclose(fit.z(target, two_sigma_above), 2.0)
    assert fit.spike_threshold(target) == fit.expected(target) + fit.sigma


def test_a_lean_season_rise_is_not_a_spike():
    # Prices rise every lean season; the seasonal norm absorbs that.
    m = M0 + np.arange(60)
    lp = 5 + SEASON[m % 12] + np.random.default_rng(3).normal(0, 0.03, 60)
    fit = fit_seasonal_trend(m, lp)
    peak = M0 + 60 + 3  # month index 3 (April) is the seasonal peak of SEASON
    assert fit.z(peak, 5 + SEASON[peak % 12]) < 1


def test_not_enough_data():
    m = M0 + np.arange(MIN_OBS - 1)
    assert fit_seasonal_trend(m, np.zeros(len(m)) + np.arange(len(m)) * 0.01) is None
    m = M0 + np.array([t for t in range(60) if t % 12 != 5])  # June never observed
    assert fit_seasonal_trend(m, np.random.default_rng(4).normal(5, 0.1, len(m))) is None


def test_fit_uses_only_the_last_ten_years():
    rng = np.random.default_rng(5)
    m = M0 + np.arange(240)
    lp = np.where(np.arange(240) < 120, 9.0, 5.0) + rng.normal(0, 0.05, 240)  # old level is far away
    fit = fit_seasonal_trend(m, lp)
    assert fit.n == 120 and abs(fit.expected(m[-1]) - 5.0) < 0.1
