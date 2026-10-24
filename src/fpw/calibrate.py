"""Recalibration of predictive distributions with the model's own past PIT values (quantile recalibration).

PIT = where the real value fell in the forecast distribution; a calibrated model has uniform PITs. If past PITs pile
up near 0 and 1 the intervals were too narrow, if they lean to one side the forecasts were biased. With G the
empirical distribution of past PITs, the recalibrated forecast is

    quantile'(tau) = quantile(G^-1(tau))        P'(value > threshold) = 1 - G(1 - P(value > threshold))

Point in time: at origin O only forecasts whose target month was published by O (target <= O - LAG) are used, from
the last WINDOW_MONTHS, per (model, country, step). Fixed before the backtest: 60 months, at least 300 PITs.
"""

import numpy as np
import pandas as pd

from fpw.backtest import LAG, Q_COLUMNS, with_pit
from fpw.baselines import REPORT_LEVELS
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS, quantile_at

WINDOW_MONTHS = 60
MIN_PITS = 300
_REPORT_IN_GRID = [int(np.argmin(np.abs(GRID_LEVELS - q))) for q in REPORT_LEVELS]


def recalibrate(fc: pd.DataFrame, by=("model", "country", "step"), window: int = WINDOW_MONTHS,
                min_pits: int = MIN_PITS, lag: int = LAG, suffix: str = "_cal") -> pd.DataFrame:
    """Recalibrated copies of the forecast rows (model name + suffix). Rows without enough past PITs keep their
    original distribution and get `calibrated = False`. Needs the columns of backtest.walk_forward, incl. `pit`."""
    out = []
    for _, g in fc.groupby(list(by), sort=False):
        g = g.sort_values("origin")
        pit, target = g["pit"].to_numpy(), g["target"].to_numpy()
        for origin, rows in g.groupby("origin", sort=False):
            known = (target <= origin - lag) & (target > origin - lag - window)
            rows = rows.copy()
            if known.sum() < min_pits:
                rows["calibrated"] = False
                out.append(rows)
                continue
            past = np.sort(pit[known])
            new_grid = quantile_at(rows[GRID_COLUMNS].to_numpy(), GRID_LEVELS, np.quantile(past, GRID_LEVELS))
            new_grid = np.maximum.accumulate(new_grid, axis=1)  # guard against tiny non-monotonicity
            rows[GRID_COLUMNS] = new_grid
            rows[Q_COLUMNS] = new_grid[:, _REPORT_IN_GRID]
            rows["spike_prob"] = 1 - np.searchsorted(past, 1 - rows["spike_prob"].to_numpy(), side="right") / len(past)
            rows["calibrated"] = True
            out.append(rows)
    res = pd.concat(out, ignore_index=True).drop(columns="pit")
    res["model"] = res["model"] + suffix
    return with_pit(res)
