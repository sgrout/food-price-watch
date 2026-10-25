import numpy as np
import pandas as pd
import pytest
from scipy.special import ndtr, ndtri

from fpw.backtest import LAG, score, summarize
from fpw.basket_model import basket_grid, basket_walk_forward, direct_walk_forward
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS

Z = ndtri(GRID_LEVELS)


def test_comonotone_is_the_sum_of_item_quantiles():
    grids = np.vstack([np.log(100) + 0.1 * Z, np.log(50) + 0.2 * Z])
    q = np.array([2.0, 3.0])
    g = basket_grid(grids, q, np.ones((2, 2)), np.random.default_rng(0))
    assert np.allclose(np.exp(g), 2 * np.exp(grids[0]) + 3 * np.exp(grids[1]))


def test_correlation_widens_the_basket_range():
    grids = np.vstack([np.log(100) + 0.15 * Z] * 2)
    q = np.array([1.0, 1.0])
    width = lambda r: np.diff(basket_grid(grids, q, np.array([[1, r], [r, 1]]), np.random.default_rng(1),
                                          n_sims=20000)[[2, 8]])[0]  # 10 % .. 90 %
    assert width(0.0) < width(0.5) < width(0.95) <= width(1.0) + 1e-9


def simulated(rho=0.8, n_origins=160, n_markets=12, seed=3):
    """Two items per market with true N(mu, s) log-price forecasts and errors correlated rho (known truth)."""
    rng = np.random.default_rng(seed)
    rows, hist = [], []
    s = np.array([0.12, 0.18])
    for mk in range(n_markets):
        bid = f"sim-{mk}-basket-b"
        for o in range(n_origins):
            origin, step = 1000 + o, 1
            target = origin - LAG + step
            e = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]])
            mu = np.log([200.0, 500.0])
            actual = mu + s * e
            hist.append({"basket_series_id": bid, "country": "sim", "market_id": mk, "market": f"M{mk}",
                         "basket_id": "b", "m": target, "cost": float(10 * np.exp(actual[0]) + 2 * np.exp(actual[1]))})
            for i, comp in enumerate(["cereal", "pulses"]):
                grid = mu[i] + s[i] * Z
                rows.append({"series_id": f"{bid}-{comp}", "country": "sim", "market_id": mk, "market": f"M{mk}",
                             "origin": origin, "step": step, "target": target, "k": 1, "model": "lgbm_cal",
                             "actual": actual[i], "pit": float(ndtr(e[i])), "eligible_at_origin": True,
                             "basket_series_id": bid, "component": comp, "quantity_in_series_unit": [10.0, 2.0][i],
                             **dict(zip(GRID_COLUMNS, grid))})
    return pd.DataFrame(rows), pd.DataFrame(hist)


@pytest.fixture(scope="module")
def sim():
    items, hist = simulated()
    out = {m: score(basket_walk_forward(items, hist, method=m)) for m in ["copula", "independence", "comonotone"]}
    return items, hist, out


def test_copula_basket_ranges_are_calibrated_when_items_are(sim):
    _, _, out = sim
    late = {m: f[f["origin"] >= 1000 + 70] for m, f in out.items()}  # after the correlation has been learned
    cover = {m: f["in80"].mean() for m, f in late.items()}
    assert abs(cover["copula"] - 0.8) < 0.04, cover
    assert cover["independence"] < cover["copula"] - 0.03 < cover["comonotone"] - 0.03, cover


def test_no_look_ahead_in_the_copula(sim):
    """Outcomes not yet published at an origin cannot change its basket forecast."""
    items, hist, out = sim
    origin = 1000 + 100
    shocked = items.copy()
    later = shocked["target"] > origin - LAG
    shocked.loc[later, "pit"] = 0.999
    hist2 = hist.copy()
    hist2.loc[hist2["m"] > origin - LAG, "cost"] *= 5
    a = basket_walk_forward(items, hist, "copula")
    b = basket_walk_forward(shocked, hist2, "copula")
    cols = ["series_id", "q10", "q50", "q90"]
    pd.testing.assert_frame_equal(a.loc[a["origin"] == origin, cols].reset_index(drop=True),
                                  b.loc[b["origin"] == origin, cols].reset_index(drop=True))


def test_a_basket_needs_every_component():
    items, hist = simulated(n_origins=5, n_markets=1)
    one = items[items["component"] == "cereal"].copy()
    one = pd.concat([one, items[(items["component"] == "pulses") & (items["origin"] != 1002)]])
    out = basket_walk_forward(one, hist, "copula")
    assert 1002 not in set(out["origin"]) and len(out) == 4


def test_direct_benchmark_runs_on_the_basket_series():
    rng = np.random.default_rng(4)
    m = 2005 * 12 + np.arange(120)
    hist = pd.DataFrame({"basket_series_id": "x-basket", "country": "mali", "market_id": 1, "market": "M1",
                         "basket_id": "b", "m": m, "cost": 3000 * np.exp(np.cumsum(rng.normal(0, 0.04, 120)))})
    fc = direct_walk_forward(hist, range(m[0] + 48, m[-1] + LAG))
    assert set(fc["model"]) == {"basket_direct"} and len(fc) and fc["series_id"].eq("x-basket").all()
    assert summarize(score(fc), by=("model",))["coverage80"].iloc[0] > 0.6
