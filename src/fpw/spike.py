"""Spike definition, ALPS-style (after WFP's Alert for Price Spikes).

Fit log price = seasonal level (one per month of the year) + linear trend on the last 10 years of usable data, and
measure how far a price is above that "usual for the season" value in residual standard deviations:

    z = (log price - expected) / sigma        normal < 0.25 <= stress < 1 <= alert < 2 <= crisis

A **spike** is z >= 1 (ALPS "alert" or worse). The fit only uses data available at the forecast origin, so the
definition itself has no look-ahead. Differences from WFP's ALPS: log prices, a 10-year window, and an AR(1) on
the residuals (used by the alps_ar1 baseline, not by the definition).
"""

from dataclasses import dataclass

import numpy as np

SPIKE_Z = 1.0
WINDOW_MONTHS = 120
MIN_OBS = 36
MIN_PER_CALENDAR_MONTH = 2


@dataclass(frozen=True)
class SeasonalTrend:
    season: np.ndarray  # 12 seasonal levels (log), index = month % 12
    trend: float  # log change per month
    m_ref: int  # the trend is 0 at this month (the last observation)
    sigma: float  # residual standard deviation
    phi: float  # lag-1 autocorrelation of the residuals, clipped to [0, 0.98]
    resid_last: float  # residual of the last observation
    n: int
    xtx_inv: np.ndarray  # (X'X)^-1 of the fit, for the uncertainty of expected()

    def expected(self, m) -> np.ndarray:
        m = np.asarray(m)
        return self.season[m % 12] + self.trend * (m - self.m_ref)

    def expected_var(self, m) -> np.ndarray:
        """Variance of expected(m) from parameter uncertainty: sigma^2 x' (X'X)^-1 x."""
        m = np.atleast_1d(m)
        x = np.column_stack([np.eye(12)[m % 12], m - self.m_ref])
        return self.sigma ** 2 * np.einsum("ij,jk,ik->i", x, self.xtx_inv, x)

    def z(self, m, lp) -> np.ndarray:
        return (np.asarray(lp) - self.expected(m)) / self.sigma

    def spike_threshold(self, m) -> np.ndarray:
        return self.expected(m) + SPIKE_Z * self.sigma


def fit_seasonal_trend(m: np.ndarray, lp: np.ndarray, window: int = WINDOW_MONTHS) -> SeasonalTrend | None:
    """Least-squares fit on the observations in the last `window` months; None if there is not enough data
    (fewer than MIN_OBS observations, or a calendar month seen fewer than MIN_PER_CALENDAR_MONTH times)."""
    m, lp = np.asarray(m), np.asarray(lp, dtype=float)
    keep = m > m.max() - window
    m, lp = m[keep], lp[keep]
    month = m % 12
    if len(m) < MIN_OBS or np.bincount(month, minlength=12).min() < MIN_PER_CALENDAR_MONTH:
        return None
    m_ref = int(m.max())
    X = np.column_stack([np.eye(12)[month], m - m_ref])
    beta, *_ = np.linalg.lstsq(X, lp, rcond=None)
    resid = lp - X @ beta
    sigma = float(np.sqrt(resid @ resid / (len(m) - 13)))
    if not sigma > 0:
        return None
    # lag-1 autocorrelation from consecutive months only
    pos = {int(t): r for t, r in zip(m, resid)}
    pairs = np.array([(pos[t], pos[t + 1]) for t in pos if t + 1 in pos])
    phi = float(np.clip((pairs[:, 0] @ pairs[:, 1]) / (pairs[:, 0] @ pairs[:, 0]), 0, 0.98)) if len(pairs) > 12 else 0.0
    return SeasonalTrend(beta[:12], float(beta[12]), m_ref, sigma, phi, float(resid[-1]), len(m),
                         np.linalg.pinv(X.T @ X))
