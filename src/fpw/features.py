"""Forecast cases with features for the pooled model: one row per (series, origin, step).

All features of a case use only data up to its last usable month (origin - LAG); the target is the log change from
the last observation to the target month. Cases whose target was not (yet) observed are kept (actual = NaN): they
count for the cross-market features and are what a live forecast predicts.
"""

import numpy as np
import pandas as pd

from fpw.backtest import LAG, MAX_STALENESS, MIN_HISTORY, STEPS
from fpw.baselines import LEVELS, seasonal_rw
from fpw.spike import fit_seasonal_trend

# Commodity groups, first match wins ("Maize flour" -> maize, "Cassava flour" -> cassava, "Wheat flour" -> wheat).
GROUPS = ["cassava", "wheat", "maize", "rice", "millet", "sorghum", "beans", "oil", "flour"]
_Q10, _Q50, _Q90 = (int(np.argmin(np.abs(LEVELS - q))) for q in (0.1, 0.5, 0.9))

FEATURES = [
    "step", "k", "target_month", "n_hist", "z_now", "resid_last", "sigma", "phi", "seas_change",
    "ret1", "ret3", "ret6", "ret12", "vol12", "srw_change", "srw_width80",
    "grp_ret1", "grp_ret3", "grp_z", "grp_n", "country", "commodity_group",
]
CATEGORICAL = ["country", "commodity_group"]


def commodity_group(name: str) -> str:
    lower = name.lower()
    return next((g for g in GROUPS if g in lower), "other")


def build_cases(panel: pd.DataFrame, origins, lag: int = LAG, steps=STEPS, min_history: int = MIN_HISTORY,
                max_staleness: int = MAX_STALENESS) -> pd.DataFrame:
    """Cases for every (series, origin) that also qualifies for the baselines (same history rules, a seasonal fit)."""
    steps = np.asarray(steps)
    out = []
    for sid, g in panel.groupby("series_id", sort=False):
        m, lp = g["m"].to_numpy(), g["lp"].to_numpy()
        m0 = int(m[0])
        full = np.full(int(m[-1]) - m0 + 1, np.nan)
        full[m - m0] = lp
        country, commodity = g["country"].iloc[0], g["commodity"].iloc[0]
        group = commodity_group(commodity)
        for origin in origins:
            m_data = origin - lag
            n_hist = int(np.searchsorted(m, m_data, side="right"))
            if n_hist < min_history or m_data - m[n_hist - 1] > max_staleness:
                continue
            m_last = int(m[n_hist - 1])
            fit = fit_seasonal_trend(m[:n_hist], lp[:n_hist])
            if fit is None:
                continue
            arr = full[: m_last - m0 + 1]
            lp_last = arr[-1]
            back = {j: arr[-1 - j] if len(arr) > j else np.nan for j in (1, 3, 6, 12)}
            d1 = np.diff(arr[-13:])
            vol12 = np.nanstd(d1) if np.sum(~np.isnan(d1)) >= 6 else np.nan
            targets = m_data + steps
            ks = targets - m_last
            srw = seasonal_rw(arr, m0, ks)
            expected = fit.expected(targets)
            seas_change = expected - fit.expected(m_last)
            for i, step in enumerate(steps):
                t = int(targets[i])
                out.append((sid, country, commodity, group, origin, int(step), t, int(ks[i]), m_last, lp_last,
                            full[t - m0] if t <= m[-1] else np.nan, expected[i], fit.sigma, fit.phi, fit.resid_last,
                            fit.resid_last / fit.sigma, n_hist, t % 12, seas_change[i],
                            lp_last - back[1], lp_last - back[3], lp_last - back[6], lp_last - back[12], vol12,
                            srw[i, _Q50] - lp_last if srw is not None else np.nan,
                            srw[i, _Q90] - srw[i, _Q10] if srw is not None else np.nan))
    cols = ["series_id", "country", "commodity", "commodity_group", "origin", "step", "target", "k", "m_last",
            "lp_last", "actual", "expected", "sigma", "phi", "resid_last", "z_now", "n_hist", "target_month",
            "seas_change", "ret1", "ret3", "ret6", "ret12", "vol12", "srw_change", "srw_width80"]
    cases = pd.DataFrame(out, columns=cols)
    return add_group_features(cases)


def add_group_features(cases: pd.DataFrame) -> pd.DataFrame:
    """How the same food moves in the country's other markets at the origin: medians over series, one value per
    (series, origin) so that steps do not count several times."""
    per_series = cases.drop_duplicates(["series_id", "origin"])
    grp = per_series.groupby(["country", "commodity_group", "origin"]).agg(
        grp_ret1=("ret1", "median"), grp_ret3=("ret3", "median"), grp_z=("z_now", "median"),
        grp_n=("series_id", "size"))
    return cases.join(grp, on=["country", "commodity_group", "origin"])
