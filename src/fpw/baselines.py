"""Baseline forecasters: predictive quantiles of the log price k months after the last observation.

Candidates, fixed before the backtest:
- naive:        last value; errors = the series' de-medianed 1-month changes scaled by sqrt(k) (random walk).
- seasonal_rw:  last value + the average k-month change for this calendar month + de-seasonalised changes.
- alps_ar1:     seasonal trend (fpw.spike) + the current residual decaying with AR(1); Gaussian errors.

Each takes the history as a dense monthly array `arr` (NaN = missing; first element = month m0, last element =
the last observation) and returns a (len(ks), len(LEVELS)) array of quantiles, or None if there is not enough data.
"""

from statistics import NormalDist

import numpy as np

from fpw.spike import SeasonalTrend

LEVELS = np.unique(np.round(np.concatenate([np.arange(1, 100) / 100, [0.025, 0.975]]), 3))
REPORT_LEVELS = (0.025, 0.1, 0.5, 0.9, 0.975)
_Z = np.array([NormalDist().inv_cdf(q) for q in LEVELS])
MIN_CHANGES = 24  # historical k-month changes needed for empirical quantiles
MIN_SAME_MONTH = 3  # changes from the same calendar month needed for a seasonal mean


def _changes(arr: np.ndarray, k: int) -> np.ndarray:
    """k-month changes d[i] = arr[i + k] - arr[i] (NaN where either end is missing)."""
    return arr[k:] - arr[:-k]


def naive(arr: np.ndarray, m0: int, ks, fit: SeasonalTrend | None = None) -> np.ndarray | None:
    # Overlapping k-month changes from a short history understate the spread (and their mean adds a noisy drift),
    # so the 1-month changes are used and scaled: a random walk's k-month spread grows with sqrt(k).
    d = _changes(arr, 1)
    d = d[~np.isnan(d)]
    if len(d) < MIN_CHANGES:
        return None
    errors = np.quantile(d, LEVELS) - np.median(d)
    return arr[-1] + np.sqrt(np.asarray(ks, dtype=float))[:, None] * errors[None, :]


def seasonal_rw(arr: np.ndarray, m0: int, ks, fit: SeasonalTrend | None = None) -> np.ndarray | None:
    m_last = m0 + len(arr) - 1
    out = []
    for k in ks:
        d = _changes(arr, k)
        start_month = (m0 + np.arange(len(d))) % 12
        ok = ~np.isnan(d)
        d, start_month = d[ok], start_month[ok]
        if len(d) < MIN_CHANGES:
            return None
        counts = np.bincount(start_month, minlength=12)
        sums = np.bincount(start_month, weights=d, minlength=12)
        mu = np.where(counts >= MIN_SAME_MONTH, sums / np.maximum(counts, 1), d.mean())
        resid = d - mu[start_month]
        out.append(arr[-1] + mu[m_last % 12] + np.quantile(resid, LEVELS))
    return np.array(out)


def alps_ar1(arr: np.ndarray, m0: int, ks, fit: SeasonalTrend | None = None) -> np.ndarray | None:
    if fit is None:
        return None
    m_last = m0 + len(arr) - 1
    ks = np.asarray(ks)
    mean = fit.expected(m_last + ks) + fit.phi ** ks * fit.resid_last
    # Stationary AR(1) residual with sd sigma: the k-step forecast error has variance sigma^2 (1 - phi^2k), plus the
    # uncertainty of the fitted seasonal trend at the target month.
    sd = np.sqrt(fit.sigma ** 2 * (1 - fit.phi ** (2 * ks)) + fit.expected_var(m_last + ks))
    return mean[:, None] + sd[:, None] * _Z[None, :]


MODELS = {"naive": naive, "seasonal_rw": seasonal_rw, "alps_ar1": alps_ar1}


def prob_above(quantiles: np.ndarray, threshold: float) -> float:
    """P(value > threshold) from a quantile grid over LEVELS (tails beyond the grid get half the outer step)."""
    cdf = np.interp(threshold, quantiles, LEVELS, left=LEVELS[0] / 2, right=1 - (1 - LEVELS[-1]) / 2)
    return float(1 - cdf)
