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

from fpw.backtest import IRREGULAR_BELOW
from fpw.countries import COUNTRIES
from fpw.explain import export_price, export_prob
from fpw.features import commodity_group
from fpw.panel import month_index
from fpw.signals import MEDIAN_MONTHS, Signals, describe_signals, signal_facts
from fpw.texts import ATTRIBUTION as ATTRIBUTION_I18N
from fpw.texts import COMMODITY_FR, COUNTRY_NOTES
from fpw.texts import DISCLAIMER as DISCLAIMER_I18N

SCHEMA_VERSION = "1.6"  # 1.1: status null without a forecast; 1.2: French, reporting regularity; 1.3: status "beta";
# 1.4: market signals (national gap, silence), silent series kept with history only; 1.5: any country id, country note;
# 1.6: data_up_to per country (lgbm_fresh2), 4 or 5 forecast rows
STATUSES = ("preview", "beta", "published")  # preview: not public; beta: public with a beta banner; published
ATTRIBUTION = ATTRIBUTION_I18N["en"]
LICENSE = {"data": "CC BY-IGO 3.0 (WFP)", "url": "https://creativecommons.org/licenses/by/3.0/igo/"}
SOURCES = ["https://data.humdata.org/organization/wfp"]
DISCLAIMER = DISCLAIMER_I18N["en"]
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
    return None if x is None or pd.isna(x) else export_price(x)


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
                 status: str = "preview", signals: Signals | None = None,
                 silent: pd.DataFrame | None = None, model: str = "lgbm_cal",
                 track_period: str = "2023-01 onwards") -> dict[str, bytes]:
    """All export files as {path: bytes}; manifest.json lists every other file with its size and sha256.

    summary: gold.live_summary; forecasts: the latest run of gold.live_forecasts, model lgbm_cal; prices: silver
    retail prices (at least of the summary and silent series; with admin1, admin2, latitude, longitude);
    metrics / metrics_country: gold.backtest_metrics(_country) population 'eligible'; live_metrics: gold.live_metrics
    (may be empty). signals: fpw.signals.compute_signals (None = no signals); silent: fpw.signals.silent_series,
    series that stopped reporting, exported with history only so they stay visible. model: the product whose track
    record is exported. `data_up_to` is per country (summary `data_month`); top-level files carry the newest.
    """
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    files: dict[str, bytes] = {}
    origin = int(summary["origin"].iloc[0])
    data_month = summary.groupby("country")["data_month"].max().astype(int).to_dict()
    data_up_to = max(data_month.values())
    model_version = str(summary["model_version"].iloc[0])
    run_at = pd.Timestamp(summary["run_at"].iloc[0]).isoformat()
    if silent is not None and len(silent):
        first = summary.iloc[0]
        for c in set(silent["country"]) - set(data_month):  # a country without forecasts: its reference month
            data_month[c] = signals.reference[c]
        summary = pd.concat([summary, pd.DataFrame({
            "series_id": silent["series_id"], "country": silent["country"], "market_id": silent["market_id"],
            "series_commodity_id": silent["series_commodity_id"], "unit": silent["unit"], "market": silent["market"],
            "commodity": silent["commodity"], "commodity_group": silent["commodity"].map(commodity_group),
            "currency": silent["country"].map(lambda c: COUNTRIES[c].currencies[0]), "eligible_at_origin": False,
            "status": None, "level_pct": 0, "explanation": "", "explanation_fr": "",
            "months_reported_12": silent["months_reported_12"], "last_obs_month": silent["m_last"],
            "data_month": silent["country"].map(data_month),
            **{c: first[c] for c in ["origin", "model_version", "run_at"]}})], ignore_index=True)
    key = ["country", "market_id", "series_commodity_id", "unit"]
    prices = prices.sort_values("date")
    by_series = {k: g for k, g in prices.groupby(key, sort=False)}
    gaps = signals.gaps.set_index("series_id") if signals is not None else pd.DataFrame()
    quiet = signals.markets.set_index(["country", "market_id"]) if signals is not None else pd.DataFrame()
    medians = {k: g for k, g in signals.medians.groupby(["country", "series_commodity_id", "unit"])} \
        if signals is not None else {}
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
                    "spike_probability": export_prob(f.spike_prob) if show else None, "show_spike_probability": show,
                })
                csv_rows.append({
                    "series_id": sid, "country": s.country, "admin1": place["admin1"] if place is not None else "",
                    "market": s.market, "commodity": s.commodity, "unit": s.unit, "currency": s.currency,
                    "month": month_str(f.target), "horizon": HORIZONS[int(f.step)],
                    "p025": _price(np.exp(f.q025)), "p10": _price(np.exp(f.q10)), "p50": _price(np.exp(f.q50)),
                    "p90": _price(np.exp(f.q90)), "p975": _price(np.exp(f.q975)),
                    "usual_level": _price(np.exp(f.expected)),
                    "spike_probability": export_prob(f.spike_prob) if show else "", "status_now": s.status, **common,
                    "data_up_to": month_str(data_month[s.country]),
                })
        next_fc = next((f for f in forecast if f["step"] == SPIKE_STEP), None)
        gap_row = gaps.loc[s.series_id] if s.series_id in gaps.index else None
        quiet_row = quiet.loc[(s.country, s.market_id)] if (s.country, s.market_id) in quiet.index else None
        sf = signal_facts(gap_row, quiet_row, signals.reference.get(s.country) if signals else None, s.country)
        med = medians.get((s.country, s.series_commodity_id, s.unit))
        first_m = month_index(pd.Series([hist["date"].iloc[0]])).iloc[0] if len(hist) else data_up_to + 1
        national = [] if med is None else [
            {"month": month_str(r.m), "price": _price(np.exp(r.median_lp))}
            for r in med[(med["m"] >= max(first_m, data_month[s.country] - MEDIAN_MONTHS + 1))
                         & (med["m"] <= data_month[s.country])]
            .sort_values("m").itertuples()]
        doc_signals = {
            "national_gap": None if sf["gap"] is None else {
                "month": month_str(sf["gap"]["month"]), "pct": sf["gap"]["pct"], "usual_pct": sf["gap"]["usual_pct"],
                "n_markets": sf["gap"]["n"], "far_above_usual": sf["gap"]["far_above_usual"]},
            "silence": None if sf["silence"] is None else {
                "months": sf["silence"]["months"], "last_reported_month": month_str(sf["silence"]["last_month"]),
                "reference_month": month_str(sf["silence"]["reference"])},
            "text": {"en": describe_signals(sf, "en"), "fr": describe_signals(sf, "fr")},
        } if signals is not None else None
        doc = {
            "schema_version": SCHEMA_VERSION, "id": sid,
            "country": {"id": s.country, "name": COUNTRIES[s.country].name},
            "market": {"id": int(s.market_id), "name": s.market,
                       "admin1": place["admin1"] if place is not None else None,
                       "admin2": place["admin2"] if place is not None else None,
                       "latitude": _round(place["latitude"], 4) if place is not None else None,
                       "longitude": _round(place["longitude"], 4) if place is not None else None},
            "commodity": {"id": int(s.series_commodity_id), "name": s.commodity,
                          "name_fr": COMMODITY_FR.get(s.commodity, s.commodity), "group": s.commodity_group},
            "unit": s.unit, "currency": s.currency, "price_type": "retail",
            "eligible": bool(s.eligible_at_origin),
            # No status without enough data: the usual level then comes from an unreliable seasonal fit.
            "status": ({"code": s.status, "level_vs_usual_pct": int(s.level_pct), "month": month_str(s.last_obs_month)}
                       if s.eligible_at_origin else None),
            "explanation": {"en": s.explanation, "fr": s.explanation_fr} if s.eligible_at_origin else {},
            "reporting": {"months_reported_12": int(s.months_reported_12),
                          "irregular": int(s.months_reported_12) < IRREGULAR_BELOW},
            "signals": doc_signals,
            "dates": {**common, "data_up_to": month_str(data_month[s.country]),
                      "last_observed_month": month_str(s.last_obs_month), "run_at": run_at},
            "history": history, "national_median": national, "forecast": forecast,
            "attribution": ATTRIBUTION,
        }
        files[f"series/{sid}.json"] = _json(doc)
        index.append({
            "id": sid, "country": s.country, "market": s.market, "admin1": doc["market"]["admin1"],
            "commodity": s.commodity, "commodity_fr": doc["commodity"]["name_fr"], "commodity_group": s.commodity_group,
            "unit": s.unit, "currency": s.currency,
            "months_reported_12": doc["reporting"]["months_reported_12"],
            "irregular_reporting": doc["reporting"]["irregular"],
            "eligible": bool(s.eligible_at_origin), "status": s.status if s.eligible_at_origin else None,
            "last_observed_month": month_str(s.last_obs_month),
            "next_month": next_fc["month"] if next_fc else None, "next_p10": next_fc["p10"] if next_fc else None,
            "next_p50": next_fc["p50"] if next_fc else None, "next_p90": next_fc["p90"] if next_fc else None,
            "next_spike_probability": next_fc["spike_probability"] if next_fc else None,
            "gap_pct": sf["gap"]["pct"] if sf["gap"] else None,
            "far_above_usual": bool(sf["gap"] and sf["gap"]["far_above_usual"]),
            "silent_months": sf["silence"]["months"] if sf["silence"] else None,
            "latitude": doc["market"]["latitude"], "longitude": doc["market"]["longitude"],
        })

    files["index.json"] = _json({"schema_version": SCHEMA_VERSION, **common, "series": index,
                                 "attribution": ATTRIBUTION})
    for c in sorted({r["country"] for r in index}):  # small per-country lists for phone pages
        files[f"index/{c}.json"] = _json({"schema_version": SCHEMA_VERSION, **common,
                                          "series": [r for r in index if r["country"] == c], "attribution": ATTRIBUTION})

    countries = []
    idx = pd.DataFrame(index)
    admin1_of = prices.groupby(["country", "market_id"])["admin1"].last() if "admin1" in prices else pd.Series()
    for c, g in idx.groupby("country"):
        el = g[g["eligible"]]
        listed = signals.markets[(signals.markets["country"] == c) & signals.markets["listed"]] \
            if signals is not None else pd.DataFrame(columns=["market_id", "market", "months", "last_month"])
        countries.append({
            "id": c, "name": COUNTRIES[c].name, "currency": COUNTRIES[c].currencies[0],
            "series": len(g), "series_with_forecast": len(el), "markets": int(g["market"].nunique()),
            "status_counts": {k: int((el["status"] == k).sum()) for k in ["normal", "stress", "alert", "crisis"]},
            "last_observed_month": g["last_observed_month"].max(),
            "data_up_to": month_str(data_month[c]),
            "reference_month": month_str(signals.reference[c]) if signals is not None and c in signals.reference
            else None,
            "note": COUNTRY_NOTES.get(c),
            "far_above_usual": int(g["far_above_usual"].sum()),
            "silent_markets": [{"market_id": int(r.market_id), "market": r.market,
                                "admin1": admin1_of.get((c, r.market_id)), "months": int(r.months),
                                "last_reported_month": month_str(r.last_month)}
                               for r in listed.sort_values(["months", "market"], ascending=[False, True]).itertuples()],
        })
    files["countries.json"] = _json({"schema_version": SCHEMA_VERSION, **common, "countries": countries,
                                     "attribution": ATTRIBUTION})

    bt = metrics[(metrics["population"] == "eligible") & (metrics["model"] == model)
                 & (metrics["split"] == "holdout")]
    bc = metrics_country[(metrics_country["population"] == "eligible") & (metrics_country["model"] == model)
                         & (metrics_country["split"] == "holdout")]
    lv = live_metrics[(live_metrics["population"] == "eligible") & (live_metrics["model"] == model)] \
        if len(live_metrics) else live_metrics
    by_reporting = {}
    for name in ("regular", "irregular"):
        part = metrics[(metrics["population"] == f"eligible_{name}") & (metrics["model"] == model)
                       & (metrics["split"] == "holdout")]
        by_reporting[name] = _track_rows(part)
    files["track_record.json"] = _json({
        "schema_version": SCHEMA_VERSION, "model": model, **common,
        "backtest": {
            "period": track_period, "population": "series eligible for publication at the forecast date",
            "method": "walk-forward: each forecast made with only the data published by then",
            "by_horizon": _track_rows(bt),
            "by_country": {c: _track_rows(g) for c, g in bc.groupby("country")},
            "by_reporting": by_reporting,
            "irregular_definition": f"a price published in fewer than {IRREGULAR_BELOW} of the last 12 months",
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
        f"Staple Signals forecasts (staplesignals.org), generated {stamp}.\n{ATTRIBUTION}\n{DISCLAIMER}\n"
        "Prices are in local currency per unit (nominal). p10-p90 = 80 % range, p025-p975 = 95 % range.\n"
        "spike_probability is given for next month only. Columns: see docs/export-contract.md.\n\n"
        f"Prévisions Staple Signals (staplesignals.org), générées le {stamp}.\n{ATTRIBUTION_I18N['fr']}\n{DISCLAIMER_I18N['fr']}\n"
        "Prix en monnaie locale par unité (nominaux). p10-p90 = intervalle à 80 %, p025-p975 = intervalle à 95 %.\n"
        "spike_probability (probabilité de flambée) est donnée pour le mois prochain seulement.\n").encode("utf-8")

    files["manifest.json"] = _json({
        "schema_version": SCHEMA_VERSION, "status": status, "generated_at": pd.Timestamp(generated_at).isoformat(),
        **common, "run_at": run_at, "countries": sorted(idx["country"].unique().tolist()),
        "counts": {"series": len(index), "series_with_forecast": int(idx["eligible"].sum())},
        "attribution": ATTRIBUTION, "attribution_fr": ATTRIBUTION_I18N["fr"], "license": LICENSE, "sources": SOURCES,
        "disclaimer": DISCLAIMER, "disclaimer_fr": DISCLAIMER_I18N["fr"],
        "missing_translations": sorted({r["commodity"] for r in index if r["commodity"] not in COMMODITY_FR}),
        "files": [{"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                  for p, b in sorted(files.items())],
    })
    return files


PUBLIC_COUNTRIES = ("mali", "burkina-faso", "burundi", "niger")  # job parameter public_countries; others need the owner's go


def public_scope(frames: dict[str, pd.DataFrame], countries) -> dict[str, pd.DataFrame]:
    """Keep only the rows of public countries in every frame with a `country` column; frames keyed by `series_id`
    only (forecasts) follow the series of the kept frames. Ingest, backtest and live forecasts cover every country;
    the public exports only the countries the owner approved."""
    keep = set(countries)
    out = {k: (f[f["country"].isin(keep)] if "country" in f.columns else f) for k, f in frames.items()}
    ids = set().union(*(set(f["series_id"]) for f in out.values() if "country" in f.columns and "series_id" in f))
    return {k: (f[f["series_id"].isin(ids)] if "country" not in f.columns and "series_id" in f.columns else f)
            for k, f in out.items()}


def to_tarball(files: dict[str, bytes]) -> bytes:
    """A gzipped tar of the export (fixed mtime, sorted paths: same content -> same bytes)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(files):
            info = tarfile.TarInfo(name=path)
            info.size, info.mtime, info.mode = len(files[path]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[path]))
    return buf.getvalue()
