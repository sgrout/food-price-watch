"""Walk-forward backtest of the baselines: forecasts as they could have been made at each origin month.

At origin month O only data up to month O - LAG is usable (publication lag, "month M usable from M+2"). Steps are
counted from that last usable month: steps 1-2 are a nowcast (months not yet published at O), steps 3-5 the
forecast for the next 1-3 calendar months. Every model is refit at every origin on the data before it.

Splits by target month: dev (< 2020, free to look at), validation (2020-2022, choose the model), holdout (2023+,
checked once). There is no training across series here, so no purge is needed; Phase 3 models must purge.
"""

import numpy as np
import pandas as pd

from fpw.baselines import LEVELS, MODELS, REPORT_LEVELS, prob_above
from fpw.coverage import MIN_COMPLETENESS, MIN_MONTHS
from fpw.distribution import GRID_COLUMNS, GRID_LEVELS, cdf_at
from fpw.spike import SPIKE_Z, fit_seasonal_trend

LAG = 2
STEPS = np.array([1, 2, 3, 4, 5])
MIN_HISTORY = 36  # observations up to the last usable month
MAX_STALENESS = 2  # the last observation may be at most this many months before the last usable month
VALIDATION_START, HOLDOUT_START = 2020, 2023
_REPORT_IDX = [int(np.argmin(np.abs(LEVELS - q))) for q in REPORT_LEVELS]
_GRID_IDX = [int(np.argmin(np.abs(LEVELS - q))) for q in GRID_LEVELS]
Q_COLUMNS = ["q025", "q10", "q50", "q90", "q975"]
# Identity of a series carried into every forecast row, so forecasts can be grouped by market (e.g. a food basket).
SERIES_INFO = ["market_id", "market", "series_commodity_id", "unit"]


def split_of(target_m: pd.Series) -> pd.Series:
    year = target_m // 12
    return pd.Series(np.select([year < VALIDATION_START, year < HOLDOUT_START], ["dev", "validation"], "holdout"),
                     index=target_m.index)


def series_arrays(g: pd.DataFrame):
    """Per series: months, log prices, month each value is known to be suspect (inf = never), dense arrays of all
    values and of the values that are never suspect (the only ones scored as targets)."""
    m, lp = g["m"].to_numpy(), g["lp"].to_numpy()
    sus = g["suspect_from"].to_numpy(dtype=float) if "suspect_from" in g else np.full(len(m), np.nan)
    sus = np.where(np.isnan(sus), np.inf, sus)
    m0 = int(m[0])
    full = np.full(int(m[-1]) - m0 + 1, np.nan)
    full[m - m0] = lp
    clean = full.copy()
    clean[m[np.isfinite(sus)] - m0] = np.nan
    return m, lp, sus, m0, full, clean


def history_at(m, lp, sus, m0, full, m_data, min_history=MIN_HISTORY, max_staleness=MAX_STALENESS):
    """The history usable when the last published month is m_data: observations up to m_data minus those already
    known to be data errors (sus <= m_data). A suspect value whose confirming month comes later is still used, as a
    live run would. Returns (months, log prices, dense array up to the last observation, eligible) or None.

    `eligible` applies the publication rule (fpw.coverage) to this history, so the track record can be shown for
    the series that would have been published at that origin.
    """
    upto = int(np.searchsorted(m, m_data, side="right"))
    known_bad = sus[:upto] <= m_data
    mh, lph = m[:upto][~known_bad], lp[:upto][~known_bad]
    if len(mh) < min_history or m_data - mh[-1] > max_staleness:
        return None
    m_last = int(mh[-1])
    arr = full[: m_last - m0 + 1].copy()
    bad = m[:upto][known_bad]
    arr[bad[bad <= m_last] - m0] = np.nan
    eligible = len(mh) >= MIN_MONTHS and len(mh) / (m_last - int(mh[0]) + 1) >= MIN_COMPLETENESS
    return mh, lph, arr, eligible


def walk_forward(panel: pd.DataFrame, origins, models=MODELS, lag: int = LAG, steps=STEPS,
                 min_history: int = MIN_HISTORY, max_staleness: int = MAX_STALENESS) -> pd.DataFrame:
    """One row per (series, origin, step, model) whose target month was observed (only those can be scored)."""
    steps = np.asarray(steps)
    out = []
    for sid, g in panel.groupby("series_id", sort=False):
        m, lp, sus, m0, full, clean = series_arrays(g)
        country, commodity = g["country"].iloc[0], g["commodity"].iloc[0]
        info = tuple(g[c].iloc[0] for c in SERIES_INFO)
        for origin in origins:
            m_data = origin - lag
            hist = history_at(m, lp, sus, m0, full, m_data, min_history, max_staleness)
            if hist is None:
                continue
            mh, lph, arr, eligible = hist
            targets = m_data + steps
            actual = np.array([clean[t - m0] if t <= m[-1] else np.nan for t in targets])
            if np.isnan(actual).all():
                continue
            fit = fit_seasonal_trend(mh, lph)
            if fit is None:  # no spike definition without a seasonal fit: not scored
                continue
            m_last = int(mh[-1])
            ks = targets - m_last
            expected, threshold = fit.expected(targets), fit.spike_threshold(targets)
            z_now = fit.resid_last / fit.sigma
            for name, model in models.items():
                q = model(arr, m0, ks, fit)
                if q is None:
                    continue
                for i, step in enumerate(steps):
                    if np.isnan(actual[i]):
                        continue
                    out.append((sid, country, commodity, *info, origin, int(step), int(targets[i]), int(ks[i]), name,
                                *q[i, _REPORT_IDX], prob_above(q[i], threshold[i]), actual[i], expected[i],
                                fit.sigma, z_now, eligible, *q[i, _GRID_IDX]))
    return with_pit(pd.DataFrame(out, columns=FORECAST_COLUMNS))


FORECAST_COLUMNS = ["series_id", "country", "commodity", *SERIES_INFO, "origin", "step", "target", "k", "model", *Q_COLUMNS,
                    "spike_prob", "actual", "expected", "sigma", "z_now", "eligible_at_origin", *GRID_COLUMNS]


def with_pit(fc: pd.DataFrame) -> pd.DataFrame:
    """Add the PIT: where the actual value fell in the predictive distribution (uniform if calibrated)."""
    pit = cdf_at(fc[GRID_COLUMNS].to_numpy(), GRID_LEVELS, fc["actual"].to_numpy()) if len(fc) else []
    return fc.assign(pit=pit)


def common_rows(fc: pd.DataFrame) -> pd.DataFrame:
    """Only the (series, origin, step) cases that every model forecast, so models are compared on the same cases."""
    n_models = fc["model"].nunique()
    n = fc.groupby(["series_id", "origin", "step"])["model"].transform("nunique")
    return fc[n == n_models]


def score(fc: pd.DataFrame) -> pd.DataFrame:
    """Add per-row scores: interval hits, pinball loss (mean over the report quantiles), spike outcome."""
    y = fc["actual"].to_numpy()
    pinball = np.zeros(len(fc))
    for tau, col in zip(REPORT_LEVELS, Q_COLUMNS):
        diff = y - fc[col].to_numpy()
        pinball += np.maximum(tau * diff, (tau - 1) * diff)
    z_actual = (fc["actual"] - fc["expected"]) / fc["sigma"]
    return fc.assign(
        split=split_of(fc["target"]),
        in80=(fc["q10"] <= y) & (y <= fc["q90"]),
        in95=(fc["q025"] <= y) & (y <= fc["q975"]),
        pinball=pinball / len(REPORT_LEVELS),
        abs_err=np.abs(y - fc["q50"]),
        z_actual=z_actual,
        is_spike=z_actual >= SPIKE_Z,
        spike_now=fc["z_now"] >= SPIKE_Z,
    )


def _se_over_origins(scored: pd.DataFrame, col: str) -> float:
    """Standard error of a mean, from per-origin means; overlapping k-step windows -> n_eff = n_origins / step."""
    by_origin = scored.groupby("origin")[col].mean()
    if len(by_origin) < 2:
        return float("nan")
    n_eff = max(len(by_origin) / max(int(scored["step"].iloc[0]), 1), 1.0)
    return float(by_origin.std(ddof=1) / np.sqrt(n_eff))


def _onset(p: pd.Series, s: pd.Series, alert_prob: float) -> dict:
    alert = p >= alert_prob
    return {
        "onset_n": len(s), "onset_rate": s.mean() if len(s) else np.nan,
        "onset_brier": ((p - s) ** 2).mean() if len(s) else np.nan,
        "onset_brier_climatology": ((s.mean() - s) ** 2).mean() if len(s) else np.nan,
        "onset_precision": (s & alert).sum() / alert.sum() if alert.any() else np.nan,
        "onset_recall": (s & alert).sum() / s.sum() if s.any() else np.nan,
    }


def summarize(scored: pd.DataFrame, by=("model", "split", "step"), alert_prob: float = 0.5) -> pd.DataFrame:
    """Metrics per group: coverage (with standard errors), pinball loss, median abs error, spike Brier score,
    precision/recall of alerts at `alert_prob`, and of the persistence rule 'spike now -> spike later'."""
    rows = []
    for key, g in scored.groupby(list(by)):
        p, s, now = g["spike_prob"], g["is_spike"], g["spike_now"]
        alert = p >= alert_prob
        rows.append({
            **dict(zip(by, key if isinstance(key, tuple) else (key,))),
            "n": len(g), "n_series": g["series_id"].nunique(), "n_origins": g["origin"].nunique(),
            "coverage80": g["in80"].mean(), "coverage80_se": _se_over_origins(g, "in80") if "step" in by else np.nan,
            "coverage95": g["in95"].mean(), "coverage95_se": _se_over_origins(g, "in95") if "step" in by else np.nan,
            "pinball": g["pinball"].mean(), "median_abs_err": g["abs_err"].median(),
            "spike_rate": s.mean(), "brier": ((p - s) ** 2).mean(),
            "brier_climatology": ((s.mean() - s) ** 2).mean(),
            "alert_rate": alert.mean(),
            "precision": (s & alert).sum() / alert.sum() if alert.any() else np.nan,
            "recall": (s & alert).sum() / s.sum() if s.any() else np.nan,
            "persistence_precision": (s & now).sum() / now.sum() if now.any() else np.nan,
            "persistence_recall": (s & now).sum() / s.sum() if s.any() else np.nan,
            # Onsets: series not in alert at the origin. Persistence cannot warn of these; this is early warning.
            **_onset(p[~now], s[~now], alert_prob),
        })
    return pd.DataFrame(rows)


def calibration(scored: pd.DataFrame, by=("model", "split"), bins=np.linspace(0, 1, 11)) -> pd.DataFrame:
    """Reliability table: forecast spike probability (binned) vs the observed spike frequency."""
    b = pd.cut(scored["spike_prob"], bins, include_lowest=True, labels=False)
    return (scored.assign(bin=b).groupby([*by, "bin"])
            .agg(n=("is_spike", "size"), mean_prob=("spike_prob", "mean"), observed=("is_spike", "mean"))
            .reset_index())


# Phase 3 candidates, fixed before the backtest (the other models are reported for reference only).
CANDIDATES = ("seasonal_rw", "seasonal_rw_cal", "lgbm", "lgbm_cal")


def choose_model(summary: pd.DataFrame, split: str = "validation", candidates=None) -> str:
    """The rule fixed before the backtest: lowest mean pinball loss over all steps on the validation split."""
    v = summary[summary["split"] == split]
    if candidates is not None:
        v = v[v["model"].isin(candidates)]
    return str(v.groupby("model")["pinball"].mean().idxmin())
