"""Predictive distributions given as quantile grids: CDF values and quantiles at other levels.

Interpolation is linear in normal-score space (level -> Phi^-1(level)) and extrapolates linearly beyond the outer
grid levels, i.e. Gaussian-like tails. Without extrapolation a recalibration could never widen a 95 % interval
beyond the model's own 97.5 % quantile.
"""

import numpy as np
from scipy.special import ndtr, ndtri

# Levels stored for every forecast (and predicted by the ML model); include the reported ones.
GRID_LEVELS = np.array([0.025, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95, 0.975])
GRID_COLUMNS = [f"g{round(q * 1000):03d}" for q in GRID_LEVELS]  # g025, g050, ..., g975


def _segments(z_grid: np.ndarray, z_new: np.ndarray):
    hi = np.clip(np.searchsorted(z_grid, z_new), 1, len(z_grid) - 1)
    return hi - 1, hi


def quantile_at(grid: np.ndarray, levels: np.ndarray, new_levels) -> np.ndarray:
    """Quantiles at `new_levels` for each row of `grid` (n_rows, n_levels) -> (n_rows, len(new_levels))."""
    grid = np.atleast_2d(grid)
    z, z_new = ndtri(levels), ndtri(np.clip(np.asarray(new_levels, dtype=float), 1e-6, 1 - 1e-6))
    lo, hi = _segments(z, z_new)
    w = (z_new - z[lo]) / (z[hi] - z[lo])
    return grid[:, lo] + w * (grid[:, hi] - grid[:, lo])


def cdf_at(grid: np.ndarray, levels: np.ndarray, x) -> np.ndarray:
    """P(value <= x) for each row of `grid`, with x one value per row."""
    grid = np.atleast_2d(grid)
    x = np.broadcast_to(np.asarray(x, dtype=float), (grid.shape[0],))
    z = ndtri(levels)
    n = grid.shape[1]
    hi = np.clip((grid < x[:, None]).sum(axis=1), 1, n - 1)
    lo = hi - 1
    rows = np.arange(grid.shape[0])
    q_lo, q_hi = grid[rows, lo], grid[rows, hi]
    span = q_hi - q_lo
    w = np.where(span > 0, (x - q_lo) / np.where(span > 0, span, 1), 0.5)
    return ndtr(z[lo] + w * (z[hi] - z[lo]))
