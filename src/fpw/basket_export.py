"""Basket export (optional, next to the item export): JSON files for the public site under public_export/baskets/.

Own schema version (`basket-1.0`, schemas export/schema/basket_*.schema.json). The item export is not touched.
Files: manifest.json, index/<country>.json, basket/<id>.json, track_record.json.
"""

import hashlib
from datetime import datetime

import numpy as np
import pandas as pd

from fpw.basket_texts import describe_basket, missing_components
from fpw.countries import COUNTRIES
from fpw.explain import export_price
from fpw.export import HORIZONS, LICENSE, SOURCES, STATUSES, _json, _pct, _round, month_str
from fpw.texts import ATTRIBUTION, COMMODITY_FR, DISCLAIMER

BASKET_SCHEMA_VERSION = "basket-1.0"
NEXT_STEP, LAST_STEP = 3, 5


def _track(m: pd.DataFrame) -> list[dict]:
    return [{"step": int(r.step), "horizon": HORIZONS[int(r.step)], "n": int(r.n), "coverage80": _round(r.coverage80),
             "coverage95": _round(r.coverage95), "typical_error_pct": _pct(r.median_abs_err)}
            for r in m.sort_values("step").itertuples()]


def build_basket_export(components: pd.DataFrame, history: pd.DataFrame, forecasts: pd.DataFrame,
                        metrics: pd.DataFrame, metrics_country: pd.DataFrame, live_metrics: pd.DataFrame,
                        generated_at: datetime, status: str = "beta", model: str = "basket_copula",
                        item_series=None) -> dict[str, bytes]:
    """components: fpw.basket.basket_components (+ basket_series_id); history: basket_cost_history; forecasts: the
    latest live basket rows (log cost, steps 1-5); metrics / metrics_country: basket backtest metrics (population,
    model, split, step[, country]); live_metrics may be empty. item_series: the series ids in the item export; a
    basket is exported only if all its foods are (None = no filter). As in the item export, `last_observed_month`
    and the text use the last month up to `data_up_to`; `history` keeps every published month."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    files: dict[str, bytes] = {}
    fc = forecasts[forecasts["model"] == model]
    origin = int(fc["origin"].iloc[0]) if len(fc) else None
    data_up_to = int(fc["data_month"].iloc[0]) if len(fc) and "data_month" in fc else None
    run_at = pd.Timestamp(fc["run_at"].iloc[0]).isoformat() if len(fc) and "run_at" in fc else None
    common = {"forecast_origin": month_str(origin) if origin else None,
              "data_up_to": month_str(data_up_to) if data_up_to else None}
    fc_by = {k: g.sort_values("step") for k, g in fc.groupby("series_id")}
    index = {}
    for bid, comps in components.groupby("basket_series_id", sort=True):
        if item_series is not None and not set(comps["series_id"]) <= set(item_series):
            continue
        first = comps.iloc[0]
        country = first["country"]
        currency = COUNTRIES[country].currencies[0]
        comp_list = [{"component": c.component, "commodity": c.commodity,
                      "commodity_fr": COMMODITY_FR.get(c.commodity, c.commodity),
                      "quantity": float(c.quantity), "unit": c.unit} for c in comps.itertuples()]
        h = history[history["basket_series_id"] == bid].sort_values("m")
        if h.empty:
            continue
        rows = fc_by.get(bid)
        eligible = bool(rows is not None and rows["eligible_at_origin"].all())
        forecast = []
        if eligible:
            for r in rows.itertuples():
                forecast.append({"month": month_str(r.target), "step": int(r.step), "horizon": HORIZONS[int(r.step)],
                                 **{k: export_price(np.exp(getattr(r, q))) for k, q in
                                    [("p025", "q025"), ("p10", "q10"), ("p50", "q50"), ("p90", "q90"),
                                     ("p975", "q975")]}})
        used = h[h["m"] <= data_up_to] if data_up_to is not None else h
        last = used.iloc[-1] if len(used) else h.iloc[-1]
        by_step = {f["step"]: f for f in forecast}
        facts = {"components": comp_list, "currency": currency, "last_month": int(last["m"]),
                 "cost": export_price(last["cost"]), "data_up_to": data_up_to}
        if NEXT_STEP in by_step and LAST_STEP in by_step:
            facts.update(next_month=int(rows.loc[rows["step"] == NEXT_STEP, "target"].iloc[0]),
                         next_lo=by_step[NEXT_STEP]["p10"], next_hi=by_step[NEXT_STEP]["p90"],
                         last_fc_month=int(rows.loc[rows["step"] == LAST_STEP, "target"].iloc[0]),
                         last_lo=by_step[LAST_STEP]["p10"], last_hi=by_step[LAST_STEP]["p90"])
        doc = {
            "schema_version": BASKET_SCHEMA_VERSION, "id": bid,
            "country": {"id": country, "name": COUNTRIES[country].name},
            "market": {"id": int(first["market_id"]), "name": first["market"]},
            "basket": {"basket_id": first["basket_id"], "per": "person-month", "components": comp_list,
                       "missing": missing_components(comp_list),
                       "definition": "ration-based (WFP general ration), not an official minimum expenditure basket"},
            "currency": currency, "eligible": eligible,
            "dates": {**common, "last_observed_month": month_str(last["m"]), "run_at": run_at},
            "history": [{"month": month_str(m), "cost": export_price(c)} for m, c in zip(h["m"], h["cost"])],
            "forecast": forecast,
            "explanation": {"en": describe_basket(facts, "en"), "fr": describe_basket(facts, "fr")},
            "attribution": ATTRIBUTION["en"],
        }
        files[f"basket/{bid}.json"] = _json(doc)
        nxt = by_step.get(NEXT_STEP)
        index.setdefault(country, []).append({
            "id": bid, "market": first["market"], "eligible": eligible, "currency": currency,
            "components": [c["component"] for c in comp_list], "last_observed_month": month_str(last["m"]),
            "last_cost": export_price(last["cost"]), "next_month": nxt["month"] if nxt else None,
            "next_p10": nxt["p10"] if nxt else None, "next_p50": nxt["p50"] if nxt else None,
            "next_p90": nxt["p90"] if nxt else None})
    for country, rows in index.items():
        files[f"index/{country}.json"] = _json({"schema_version": BASKET_SCHEMA_VERSION, **common,
                                                "baskets": rows, "attribution": ATTRIBUTION["en"]})
    pick = lambda df: df[(df["population"] == "eligible") & (df["model"] == model) & (df["split"] == "holdout")]
    lv = live_metrics[(live_metrics["population"] == "eligible") & (live_metrics["model"] == model)] \
        if len(live_metrics) else live_metrics
    files["track_record.json"] = _json({
        "schema_version": BASKET_SCHEMA_VERSION, "model": model, **common,
        "backtest": {"period": "2023-01 onwards", "population": "baskets whose items were all eligible at the forecast date",
                     "by_horizon": _track(pick(metrics)),
                     "by_country": {c: _track(g) for c, g in pick(metrics_country).groupby("country")}},
        "live": {"by_horizon": _track(lv) if len(lv) else []},
        "attribution": ATTRIBUTION["en"],
    })
    files["manifest.json"] = _json({
        "schema_version": BASKET_SCHEMA_VERSION, "status": status, "generated_at": pd.Timestamp(generated_at).isoformat(),
        **common, "run_at": run_at, "model": model, "countries": sorted(index),
        "counts": {"baskets": sum(len(v) for v in index.values()),
                   "baskets_with_forecast": sum(r["eligible"] for v in index.values() for r in v)},
        "attribution": ATTRIBUTION["en"], "attribution_fr": ATTRIBUTION["fr"], "license": LICENSE, "sources": SOURCES,
        "disclaimer": DISCLAIMER["en"], "disclaimer_fr": DISCLAIMER["fr"],
        "files": [{"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p, b in sorted(files.items())],
    })
    return files
