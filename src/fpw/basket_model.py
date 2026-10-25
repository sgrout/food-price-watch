"""Basket cost forecasts from the item forecasts (candidates fixed before the backtest).

- copula (product candidate): the components' calibrated item distributions, joined with the correlation of their
  past errors (normal scores of past PITs, same market and step, only targets published by the origin, last 60
  months), shrunk 50 % toward the country-pooled correlation. Simulate correlated draws -> item prices -> cost.
- independence (reference): the same with zero correlation (too narrow if errors move together).
- comonotone (reference): perfectly correlated errors = the item quantiles added up (too wide otherwise).
- direct (benchmark, fpw.basket_model.direct_walk_forward): the basket cost series itself through seasonal_rw and
  recalibration, like an item.

Rows have the backtest's forecast columns, in log cost, so fpw.backtest.score/summarize apply unchanged (the spike
columns are NaN: baskets have no spike definition).
"""

import zlib

import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri

from fpw.backtest import FORECAST_COLUMNS, LAG, Q_COLUMNS, walk_forward, with_pit
from fpw.baselines import REPORT_LEVELS, seasonal_rw
from fpw.calibrate import WINDOW_MONTHS, recalibrate
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS, quantile_at

N_SIMS = 2000
SHRINK = 0.5  # weight of the market's own correlation; the rest is the country-pooled correlation
MIN_MARKET_PAIRS = 24  # past joint errors needed for a market's own correlation (otherwise pooled only)
MIN_POOLED_PAIRS = 100  # below this, the pooled correlation is not trusted either: identity
_REPORT_IN_GRID = [int(np.argmin(np.abs(GRID_LEVELS - q))) for q in REPORT_LEVELS]


def basket_grid(item_grids: np.ndarray, quantities: np.ndarray, corr: np.ndarray, rng, n_sims: int = N_SIMS):
    """Log-cost quantile grid of sum_i quantity_i x price_i, item log-price grids (k, L) joined by a Gaussian copula
    with correlation `corr` (k, k)."""
    k = len(quantities)
    if np.allclose(corr, np.ones((k, k))):  # comonotone: exact
        cost = (quantities[:, None] * np.exp(item_grids)).sum(axis=0)
        return np.log(cost)
    chol = np.linalg.cholesky(corr + 1e-9 * np.eye(k))
    u = ndtr(rng.standard_normal((n_sims, k)) @ chol.T)
    prices = np.column_stack([np.exp(quantile_at(item_grids[i][None, :], GRID_LEVELS, u[:, i])[0]) for i in range(k)])
    cost = prices @ quantities
    return np.log(np.quantile(cost, GRID_LEVELS))


def _corr(z: np.ndarray) -> np.ndarray | None:
    if len(z) < 3:
        return None
    c = np.corrcoef(z, rowvar=False)
    return None if np.isnan(c).any() else np.atleast_2d(c)


def joint_errors(items: pd.DataFrame) -> pd.DataFrame:
    """Normal scores of the item PITs, wide: one row per (basket, origin, step), one column per component."""
    z = items.assign(z=ndtri(np.clip(items["pit"], 1e-3, 1 - 1e-3)))
    return z.pivot_table(index=["basket_series_id", "country", "origin", "step", "target"], columns="component",
                         values="z").reset_index()


def basket_walk_forward(items: pd.DataFrame, history: pd.DataFrame, method: str = "copula", lag: int = LAG,
                        window: int = WINDOW_MONTHS, seed: int = 0, only_origins=None) -> pd.DataFrame:
    """Basket forecast rows for every (basket, origin, step) where every component has a calibrated item forecast.

    items: item forecast rows (fpw.backtest columns incl. grid and pit) of the component series, joined with the
    basket components (basket_series_id, component, quantity_in_series_unit). history: fpw.basket.basket_cost_history.
    only_origins: forecast only these origins (live); the other rows only serve as past errors for the copula.
    """
    if method not in ("copula", "independence", "comonotone"):
        raise ValueError(method)
    corr_of = _CopulaCorrelation(joint_errors(items), lag, window) if method == "copula" else None
    actual = history.set_index(["basket_series_id", "m"])["cost"]
    need = items.groupby("basket_series_id")["component"].nunique()
    out = []
    wanted = None if only_origins is None else set(int(o) for o in only_origins)
    for (bid, origin, step), g in items.groupby(["basket_series_id", "origin", "step"], sort=False):
        if len(g) != need[bid] or (wanted is not None and int(origin) not in wanted):
            continue
        g = g.sort_values("component")
        k = len(g)
        if method == "comonotone":
            corr = np.ones((k, k))
        elif method == "independence" or k == 1:
            corr = np.eye(k)
        else:
            corr = corr_of(bid, g["country"].iloc[0], list(g["component"]), int(origin), int(step))
        rng = np.random.default_rng(zlib.crc32(f"{bid}|{origin}|{step}|{seed}".encode()))
        grid = basket_grid(g[GRID_COLUMNS].to_numpy(), g["quantity_in_series_unit"].to_numpy(), corr, rng)
        first = g.iloc[0]
        target = int(first["target"])
        y = actual.get((bid, target), np.nan)
        out.append({
            "series_id": bid, "country": first["country"], "commodity": "basket", "market_id": first["market_id"],
            "market": first["market"], "series_commodity_id": 0, "unit": "person-month", "origin": int(origin),
            "step": int(step), "target": target, "k": int(first["k"]), "model": f"basket_{method}",
            **dict(zip(Q_COLUMNS, grid[_REPORT_IN_GRID])), "spike_prob": np.nan,
            "actual": np.log(y) if pd.notna(y) else np.nan, "expected": np.nan, "sigma": np.nan, "z_now": np.nan,
            "eligible_at_origin": bool(g["eligible_at_origin"].all()), "months_reported_12": int(g["months_reported_12"].min())
            if "months_reported_12" in g else 12, **dict(zip(GRID_COLUMNS, grid)),
        })
    if not out:
        return pd.DataFrame(columns=FORECAST_COLUMNS + ["pit"])
    return with_pit(pd.DataFrame(out)[FORECAST_COLUMNS])


class _CopulaCorrelation:
    """Correlation of past item errors for a basket at an origin: only joint errors whose target was published by
    the origin (target <= origin - lag) within the window; the market's own correlation shrunk toward the pooled
    country one. Pooled correlations are cached per (country, step, origin)."""

    def __init__(self, errors: pd.DataFrame, lag: int, window: int):
        self.lag, self.window = lag, window
        self.by_country = {k: g.sort_values("target") for k, g in errors.groupby(["country", "step"])}
        self.by_basket = {k: g.sort_values("target") for k, g in errors.groupby(["basket_series_id", "step"])}
        self.pooled = {}

    def _window(self, frame: pd.DataFrame, origin: int) -> pd.DataFrame:
        t = frame["target"].to_numpy()
        lo, hi = np.searchsorted(t, origin - self.lag - self.window, "right"), np.searchsorted(t, origin - self.lag, "right")
        return frame.iloc[lo:hi]

    def __call__(self, bid: str, country: str, comps: list[str], origin: int, step: int) -> np.ndarray:
        key = (country, step, origin, tuple(comps))
        if key not in self.pooled:
            frame = self.by_country.get((country, step))
            known = self._window(frame, origin)[comps].dropna() if frame is not None else pd.DataFrame()
            self.pooled[key] = _corr(known.to_numpy()) if len(known) >= MIN_POOLED_PAIRS else None
        r_pool = self.pooled[key]
        frame = self.by_basket.get((bid, step))
        own = self._window(frame, origin)[comps].dropna() if frame is not None else pd.DataFrame()
        r_own = _corr(own.to_numpy()) if len(own) >= MIN_MARKET_PAIRS else None
        if r_pool is None:
            return np.eye(len(comps)) if r_own is None else r_own
        return r_pool if r_own is None else SHRINK * r_own + (1 - SHRINK) * r_pool


def basket_panel(history: pd.DataFrame) -> pd.DataFrame:
    """The basket cost series in the shape of fpw.panel.monthly_panel, so item code can forecast them directly."""
    return pd.DataFrame({
        "series_id": history["basket_series_id"], "country": history["country"], "market_id": history["market_id"],
        "series_commodity_id": 0, "commodity": "basket", "market": history["market"], "unit": "person-month",
        "m": history["m"], "lp": np.log(history["cost"]), "suspect_from": np.nan})


def direct_walk_forward(history: pd.DataFrame, origins) -> pd.DataFrame:
    """Benchmark: seasonal_rw on the basket cost series, recalibrated with its own past PITs (as for items)."""
    raw = walk_forward(basket_panel(history), origins, models={"seasonal_rw": seasonal_rw})
    raw = raw.assign(calibrated=False)
    cal = recalibrate(raw)
    return cal.assign(model="basket_direct")


def basket_items(item_forecasts: pd.DataFrame, components: pd.DataFrame, model: str = "lgbm_cal") -> pd.DataFrame:
    """The item forecast rows of `model` for every basket component, with the basket id, component name and the
    quantity in the series' unit."""
    from fpw.basket import basket_id_of
    comps = components.assign(basket_series_id=[basket_id_of(c, m, b) for c, m, b in
                                                 zip(components["country"], components["market_id"],
                                                     components["basket_id"])])
    keep = comps[["series_id", "basket_series_id", "component", "quantity_in_series_unit", "market"]]
    rows = item_forecasts[item_forecasts["model"] == model].drop(columns=["market"], errors="ignore")
    return rows.merge(keep, on="series_id", how="inner")  # market name from the basket definition
