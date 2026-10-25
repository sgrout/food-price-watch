"""Public export: the gold data a public site needs, as small JSON files and a CSV download (contract:
docs/export-contract.md, JSON Schemas in export/schema/). Pure functions; the notebook writes the files.

Only user-facing fields are exported (prices in local currency, ranges, spike chance, text, flags, track record);
no model internals. Every file carries the attribution required by the CC BY-IGO license of WFP's data.
"""

import csv
import hashlib
import io
import json
import tarfile
from datetime import datetime

import numpy as np
import pandas as pd

from fpw.countries import COUNTRIES

SCHEMA_VERSION = "1.0"
ATTRIBUTION = "Source: World Food Programme (WFP), food prices via the Humanitarian Data Exchange (HDX), CC BY-IGO."
LICENSE = {"data": "CC BY-IGO 3.0 (WFP)", "url": "https://creativecommons.org/licenses/by/3.0/igo/"}
SOURCES = ["https://data.humdata.org/organization/wfp"]
DISCLAIMER = ("Forecasts by food-price-watch, not an official WFP or FEWS NET assessment. "
              "Official assessments: https://hungermap.wfp.org and https://fews.net")
HORIZONS = {1: "nowcast_last_month", 2: "nowcast_this_month", 3: "next_month", 4: "in_2_months", 5: "in_3_months"}
SPIKE_STEP = 3  # spike chance is shown for next month only: further out, new-spike warnings are worse than the base rate
HISTORY_FLAGS = {"spike_revert": "data_error", "invalid_price": "data_error", "level_shift": "break",
                 "unconfirmed_jump": "unconfirmed_jump"}


def month_str(m: int) -> str:
    return f"{int(m) // 12:04d}-{int(m) % 12 + 1:02d}"


def series_slug(country: str, market_id: int, commodity_id: int, unit: str) -> str:
    """Stable public id (names change, ids do not): e.g. mali-247-51-retail-kg."""
    return f"{country}-{int(market_id)}-{int(commodity_id)}-retail-{unit.lower().replace(' ', '-')}"


def skill_verdict(score: float, base_rate_score: float, margin: float = 0.03) -> str:
    """Brier score vs the base-rate score (lower is better); within +-3 % counts as no difference.
    Mirrored in app/strings.py (a test checks they agree)."""
    ratio = score / base_rate_score
    if ratio < 1 - margin:
        return "better"
    if ratio > 1 + margin:
        return "worse"
    return "no_better"


def _price(x) -> float | None:
    return None if x is None or pd.isna(x) else round(float(x), 2)


def _pct(log_err) -> int | None:
    return None if pd.isna(log_err) else int(round(100 * (np.exp(float(log_err)) - 1)))


def _round(x, nd=3):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def _json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")


def _track_rows(m: pd.DataFrame) -> list[dict]:
    rows = []
    for r in m.sort_values("step").itertuples():
        rows.append({
            "step": int(r.step), "horizon": HORIZONS[int(r.step)], "n": int(r.n),
            "coverage80": _round(r.coverage80), "coverage95": _round(r.coverage95),
            "typical_error_pct": _pct(r.median_abs_err),
            "new_spike_score": _round(r.onset_brier, 4), "base_rate_score": _round(r.onset_brier_climatology, 4),
            "new_spike_verdict": skill_verdict(r.onset_brier, r.onset_brier_climatology),
        })
    return rows


def build_export(summary: pd.DataFrame, forecasts: pd.DataFrame, prices: pd.DataFrame, metrics: pd.DataFrame,
                 metrics_country: pd.DataFrame, live_metrics: pd.DataFrame, generated_at: datetime,
                 status: str = "preview") -> dict[str, bytes]:
    """All export files as {path: bytes}; manifest.json lists every other file with its size and sha256.

    summary: gold.live_summary; forecasts: the latest run of gold.live_forecasts, model lgbm_cal; prices: silver
    retail prices of the summary series (with admin1, admin2, latitude, longitude); metrics / metrics_country:
    gold.backtest_metrics(_country) population 'eligible'; live_metrics: gold.live_metrics (may be empty).
    """
    files: dict[str, bytes] = {}
    origin = int(summary["origin"].iloc[0])
    data_up_to = int(summary["data_month"].iloc[0])
    model_version = str(summary["model_version"].iloc[0])
    run_at = pd.Timestamp(summary["run_at"].iloc[0]).isoformat()
    key = ["country", "market_id", "series_commodity_id", "unit"]
    prices = prices.sort_values("date")
    by_series = {k: g for k, g in prices.groupby(key, sort=False)}
    fc_by_series = {k: g.sort_values("step") for k, g in forecasts.groupby("series_id", sort=False)}
    common = {"forecast_origin": month_str(origin), "data_up_to": month_str(data_up_to), "model_version": model_version}

    index, csv_rows = [], []
    for s in summary.itertuples():
        sid = series_slug(s.country, s.market_id, s.series_commodity_id, s.unit)
        hist = by_series.get((s.country, s.market_id, s.series_commodity_id, s.unit), prices.iloc[:0])
        place = hist.iloc[-1] if len(hist) else None
        history = [{"month": pd.Timestamp(r.date).strftime("%Y-%m"), "price": _price(r.price),
                    "flag": HISTORY_FLAGS.get(r.quality_flag) if isinstance(r.quality_flag, str) else None}
                   for r in hist.itertuples()]
        forecast = []
        if s.eligible_at_origin and s.series_id in fc_by_series:
            for f in fc_by_series[s.series_id].itertuples():
                show = int(f.step) == SPIKE_STEP
                forecast.append({
                    "month": month_str(f.target), "step": int(f.step), "horizon": HORIZONS[int(f.step)],
                    "p025": _price(np.exp(f.q025)), "p10": _price(np.exp(f.q10)), "p50": _price(np.exp(f.q50)),
                    "p90": _price(np.exp(f.q90)), "p975": _price(np.exp(f.q975)),
                    "usual_level": _price(np.exp(f.expected)), "spike_threshold": _price(np.exp(f.expected + f.sigma)),
                    "spike_probability": _round(f.spike_prob) if show else None, "show_spike_probability": show,
                })
                csv_rows.append({
                    "series_id": sid, "country": s.country, "admin1": place["admin1"] if place is not None else "",
                    "market": s.market, "commodity": s.commodity, "unit": s.unit, "currency": s.currency,
                    "month": month_str(f.target), "horizon": HORIZONS[int(f.step)],
                    "p025": _price(np.exp(f.q025)), "p10": _price(np.exp(f.q10)), "p50": _price(np.exp(f.q50)),
                    "p90": _price(np.exp(f.q90)), "p975": _price(np.exp(f.q975)),
                    "usual_level": _price(np.exp(f.expected)),
                    "spike_probability": _round(f.spike_prob) if show else "", "status_now": s.status, **common,
                })
        next_fc = next((f for f in forecast if f["step"] == SPIKE_STEP), None)
        doc = {
            "schema_version": SCHEMA_VERSION, "id": sid,
            "country": {"id": s.country, "name": COUNTRIES[s.country].name},
            "market": {"id": int(s.market_id), "name": s.market,
                       "admin1": place["admin1"] if place is not None else None,
                       "admin2": place["admin2"] if place is not None else None,
                       "latitude": _round(place["latitude"], 4) if place is not None else None,
                       "longitude": _round(place["longitude"], 4) if place is not None else None},
            "commodity": {"id": int(s.series_commodity_id), "name": s.commodity, "group": s.commodity_group},
            "unit": s.unit, "currency": s.currency, "price_type": "retail",
            "eligible": bool(s.eligible_at_origin),
            "status": {"code": s.status, "level_vs_usual_pct": int(s.level_pct), "month": month_str(s.last_obs_month)},
            "explanation": {"en": s.explanation} if s.eligible_at_origin else {},
            "dates": {**common, "last_observed_month": month_str(s.last_obs_month), "run_at": run_at},
            "history": history, "forecast": forecast,
            "attribution": ATTRIBUTION,
        }
        files[f"series/{sid}.json"] = _json(doc)
        index.append({
            "id": sid, "country": s.country, "market": s.market, "admin1": doc["market"]["admin1"],
            "commodity": s.commodity, "commodity_group": s.commodity_group, "unit": s.unit, "currency": s.currency,
            "eligible": bool(s.eligible_at_origin), "status": s.status,
            "last_observed_month": month_str(s.last_obs_month),
            "next_month": next_fc["month"] if next_fc else None, "next_p10": next_fc["p10"] if next_fc else None,
            "next_p50": next_fc["p50"] if next_fc else None, "next_p90": next_fc["p90"] if next_fc else None,
            "next_spike_probability": next_fc["spike_probability"] if next_fc else None,
            "latitude": doc["market"]["latitude"], "longitude": doc["market"]["longitude"],
        })

    files["index.json"] = _json({"schema_version": SCHEMA_VERSION, **common, "series": index,
                                 "attribution": ATTRIBUTION})

    countries = []
    idx = pd.DataFrame(index)
    for c, g in idx.groupby("country"):
        el = g[g["eligible"]]
        countries.append({
            "id": c, "name": COUNTRIES[c].name, "currency": COUNTRIES[c].currencies[0],
            "series": len(g), "series_with_forecast": len(el), "markets": int(g["market"].nunique()),
            "status_counts": {k: int((el["status"] == k).sum()) for k in ["normal", "stress", "alert", "crisis"]},
            "last_observed_month": g["last_observed_month"].max(),
        })
    files["countries.json"] = _json({"schema_version": SCHEMA_VERSION, **common, "countries": countries,
                                     "attribution": ATTRIBUTION})

    bt = metrics[(metrics["population"] == "eligible") & (metrics["model"] == "lgbm_cal")
                 & (metrics["split"] == "holdout")]
    bc = metrics_country[(metrics_country["population"] == "eligible") & (metrics_country["model"] == "lgbm_cal")
                         & (metrics_country["split"] == "holdout")]
    lv = live_metrics[(live_metrics["population"] == "eligible") & (live_metrics["model"] == "lgbm_cal")] \
        if len(live_metrics) else live_metrics
    files["track_record.json"] = _json({
        "schema_version": SCHEMA_VERSION, "model": "lgbm_cal", **common,
        "backtest": {
            "period": "2023-01 onwards", "population": "series eligible for publication at the forecast date",
            "method": "walk-forward: each forecast made with only the data published by then",
            "by_horizon": _track_rows(bt),
            "by_country": {c: _track_rows(g) for c, g in bc.groupby("country")},
        },
        "live": {"by_horizon": _track_rows(lv) if len(lv) else [],
                 "note": "Live forecasts are scored once the target month and the month after it are published."},
        "attribution": ATTRIBUTION,
    })

    out = io.StringIO()
    cols = ["series_id", "country", "admin1", "market", "commodity", "unit", "currency", "month", "horizon", "p025",
            "p10", "p50", "p90", "p975", "usual_level", "spike_probability", "status_now", "forecast_origin",
            "data_up_to", "model_version"]
    writer = csv.DictWriter(out, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv_rows)
    stamp = pd.Timestamp(generated_at).strftime("%Y-%m-%d")
    files[f"downloads/forecasts_{stamp}.csv"] = out.getvalue().encode("utf-8")
    files["downloads/README.txt"] = (
        f"food-price-watch forecasts, generated {stamp}.\n{ATTRIBUTION}\n{DISCLAIMER}\n"
        "Prices are in local currency per unit (nominal). p10-p90 = 80 % range, p025-p975 = 95 % range.\n"
        "spike_probability is given for next month only. Columns: see docs/export-contract.md.\n").encode("utf-8")

    files["manifest.json"] = _json({
        "schema_version": SCHEMA_VERSION, "status": status, "generated_at": pd.Timestamp(generated_at).isoformat(),
        **common, "run_at": run_at, "countries": sorted(idx["country"].unique().tolist()),
        "counts": {"series": len(index), "series_with_forecast": int(idx["eligible"].sum())},
        "attribution": ATTRIBUTION, "license": LICENSE, "sources": SOURCES, "disclaimer": DISCLAIMER,
        "files": [{"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                  for p, b in sorted(files.items())],
    })
    return files


def to_tarball(files: dict[str, bytes]) -> bytes:
    """A gzipped tar of the export (fixed mtime, sorted paths: same content -> same bytes)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(files):
            info = tarfile.TarInfo(name=path)
            info.size, info.mtime, info.mode = len(files[path]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[path]))
    return buf.getvalue()
