"""Simulated monthly log-price series with known properties."""

import numpy as np
import pandas as pd

SEASON = 0.15 * np.sin(2 * np.pi * np.arange(12) / 12)  # +-15 % lean-season cycle


def random_walk(n: int, sd: float, rng, start: float = 5.0) -> np.ndarray:
    return start + np.cumsum(rng.normal(0, sd, n))


def seasonal_ar1(n: int, sigma: float, phi: float, rng, trend: float = 0.005, m0: int = 2005 * 12,
                 start: float = 5.0) -> np.ndarray:
    """Seasonal level + trend + stationary AR(1) residual with marginal sd sigma."""
    r = np.empty(n)
    r[0] = rng.normal(0, sigma)
    innov = sigma * np.sqrt(1 - phi ** 2)
    for t in range(1, n):
        r[t] = phi * r[t - 1] + rng.normal(0, innov)
    m = m0 + np.arange(n)
    return start + SEASON[m % 12] + trend * np.arange(n) + r


def panel(series: dict[str, np.ndarray], m0: int = 2005 * 12) -> pd.DataFrame:
    rows = [pd.DataFrame({"series_id": sid, "country": "sim", "market_id": i, "series_commodity_id": 51,
                          "commodity": "Maize", "market": sid, "unit": "KG", "m": m0 + np.arange(len(lp)), "lp": lp})
            for i, (sid, lp) in enumerate(series.items())]
    return pd.concat(rows, ignore_index=True)
