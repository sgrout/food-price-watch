import numpy as np
import pytest
from scipy.stats import norm

from fpw.distribution import GRID_COLUMNS, GRID_LEVELS, cdf_at, quantile_at

GAUSS = norm.ppf(GRID_LEVELS)[None, :] * 0.1 + 5.0  # N(5, 0.1) as a grid


def test_grid_columns():
    assert GRID_COLUMNS[0] == "g025" and GRID_COLUMNS[5] == "g500" and GRID_COLUMNS[-1] == "g975"


def test_quantiles_of_a_gaussian_grid_are_exact_also_beyond_the_grid():
    levels = [0.001, 0.01, 0.3, 0.5, 0.99, 0.999]
    assert np.allclose(quantile_at(GAUSS, GRID_LEVELS, levels), norm.ppf(levels, 5, 0.1))


def test_cdf_of_a_gaussian_grid_is_exact_also_beyond_the_grid():
    x = np.array([4.6, 4.9, 5.0, 5.13, 5.4])
    grid = np.repeat(GAUSS, len(x), axis=0)
    assert np.allclose(cdf_at(grid, GRID_LEVELS, x), norm.cdf(x, 5, 0.1))


def test_cdf_and_quantile_are_inverse_on_a_skewed_grid():
    grid = np.exp(norm.ppf(GRID_LEVELS) * 0.5)[None, :]  # lognormal, skewed
    q = quantile_at(grid, GRID_LEVELS, [0.2, 0.7, 0.96])[0]
    assert np.allclose(cdf_at(np.repeat(grid, 3, axis=0), GRID_LEVELS, q), [0.2, 0.7, 0.96])


def test_flat_segment_does_not_divide_by_zero():
    grid = np.array([[0, 0, 0, 1, 1, 1, 1, 1, 2, 3, 4]], dtype=float)
    assert 0 <= cdf_at(grid, GRID_LEVELS, 1.0)[0] <= 1


@pytest.mark.parametrize("x", [-100.0, 100.0])
def test_extreme_values_give_tiny_tails_not_errors(x):
    p = cdf_at(GAUSS, GRID_LEVELS, x)[0]
    assert 0 <= p <= 1 and (p < 1e-6 if x < 0 else p > 1 - 1e-6)
