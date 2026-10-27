"""Generate the JSON Schemas of the public export (export/schema/*.schema.json): the contract with the public site.
Run after changing fpw/export.py: .venv/bin/python scripts/export_schemas.py (tests validate the export against them).
"""

import json
from pathlib import Path

D = Path(__file__).parents[1] / "export" / "schema"
S = "https://json-schema.org/draft/2020-12/schema"
month = {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}
nmonth = {"type": ["string", "null"], "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}
price = {"type": "number", "exclusiveMinimum": 0}
nprice = {"type": ["number", "null"], "exclusiveMinimum": 0}
prob = {"type": ["number", "null"], "minimum": 0, "maximum": 1}
status = {"enum": ["normal", "stress", "alert", "crisis"]}
version = {"const": "1.5"}
common = {"forecast_origin": month, "data_up_to": month, "model_version": {"type": "string"}}
attribution = {"type": "string", "pattern": "World Food Programme"}
country_id = {"type": "string", "pattern": "^[a-z]+(-[a-z]+)*$"}  # 1.5 / basket-1.1: any HDX country slug
horizon = {"enum": ["nowcast_last_month", "nowcast_this_month", "next_month", "in_2_months", "in_3_months"]}


def obj(props, required=None, title=None):
    o = {"type": "object", "properties": props, "required": list(props) if required is None else required,
         "additionalProperties": False}
    return {"$schema": S, "title": title, **o} if title else o


track_row = obj({"step": {"type": "integer", "minimum": 1, "maximum": 5}, "horizon": horizon,
                 "n": {"type": "integer", "minimum": 0}, "coverage80": prob, "coverage95": prob,
                 "typical_error_pct": {"type": ["integer", "null"]}, "new_spike_score": {"type": ["number", "null"]},
                 "base_rate_score": {"type": ["number", "null"]},
                 "new_spike_verdict": {"enum": ["better", "no_better", "worse"]}})

signals = obj({
    "national_gap": {"anyOf": [obj({"month": month, "pct": {"type": "integer"}, "usual_pct": {"type": ["integer", "null"]},
                                    "n_markets": {"type": "integer", "minimum": 5},
                                    "far_above_usual": {"type": "boolean"}}), {"type": "null"}]},
    "silence": {"anyOf": [obj({"months": {"type": "integer", "minimum": 2}, "last_reported_month": month,
                               "reference_month": month}), {"type": "null"}]},
    "text": obj({"en": {"type": "string"}, "fr": {"type": "string"}}),
})

SCHEMAS = {
    "manifest": obj({
        "schema_version": version, "status": {"enum": ["preview", "beta", "published"]},
        "generated_at": {"type": "string"}, **common, "run_at": {"type": "string"},
        "countries": {"type": "array", "items": country_id},
        "counts": obj({"series": {"type": "integer"}, "series_with_forecast": {"type": "integer"}}),
        "attribution": attribution, "attribution_fr": {"type": "string", "pattern": "Programme alimentaire mondial"},
        "license": obj({"data": {"type": "string"}, "url": {"type": "string"}}),
        "sources": {"type": "array", "items": {"type": "string"}}, "disclaimer": {"type": "string"},
        "disclaimer_fr": {"type": "string"},
        "missing_translations": {"type": "array", "items": {"type": "string"}},
        "files": {"type": "array", "items": obj({"path": {"type": "string"}, "bytes": {"type": "integer"},
                                                 "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})},
    }, title="food-price-watch export: manifest.json"),
    "index": obj({
        "schema_version": version, **common, "attribution": attribution,
        "series": {"type": "array", "items": obj({
            "id": {"type": "string"}, "country": country_id, "market": {"type": "string"},
            "admin1": {"type": ["string", "null"]}, "commodity": {"type": "string"}, "commodity_fr": {"type": "string"},
            "commodity_group": {"type": "string"}, "unit": {"type": "string"}, "currency": {"type": "string"},
            "months_reported_12": {"type": "integer", "minimum": 0, "maximum": 12},
            "irregular_reporting": {"type": "boolean"},
            "eligible": {"type": "boolean"}, "status": {"enum": [*status["enum"], None]},  # null if not eligible
            "last_observed_month": month,
            "next_month": nmonth, "next_p10": nprice, "next_p50": nprice, "next_p90": nprice,
            "next_spike_probability": prob,
            "gap_pct": {"type": ["integer", "null"]}, "far_above_usual": {"type": "boolean"},
            "silent_months": {"type": ["integer", "null"], "minimum": 2},
            "latitude": {"type": ["number", "null"]}, "longitude": {"type": ["number", "null"]}})},
    }, title="food-price-watch export: index.json"),
    "countries": obj({
        "schema_version": version, **common, "attribution": attribution,
        "countries": {"type": "array", "items": obj({
            "id": country_id, "name": {"type": "string"}, "currency": {"type": "string"},
            "series": {"type": "integer"}, "series_with_forecast": {"type": "integer"},
            "markets": {"type": "integer"},
            "status_counts": obj({k: {"type": "integer"} for k in ["normal", "stress", "alert", "crisis"]}),
            "last_observed_month": month, "reference_month": nmonth,
            "note": {"anyOf": [obj({"en": {"type": "string"}, "fr": {"type": "string"}}), {"type": "null"}]},
            "far_above_usual": {"type": "integer", "minimum": 0},
            "silent_markets": {"type": "array", "items": obj({
                "market_id": {"type": "integer"}, "market": {"type": "string"}, "admin1": {"type": ["string", "null"]},
                "months": {"type": "integer", "minimum": 2}, "last_reported_month": month})}})},
    }, title="food-price-watch export: countries.json"),
    "series": obj({
        "schema_version": version, "id": {"type": "string"},
        "country": obj({"id": country_id, "name": {"type": "string"}}),
        "market": obj({"id": {"type": "integer"}, "name": {"type": "string"}, "admin1": {"type": ["string", "null"]},
                       "admin2": {"type": ["string", "null"]}, "latitude": {"type": ["number", "null"]},
                       "longitude": {"type": ["number", "null"]}}),
        "commodity": obj({"id": {"type": "integer"}, "name": {"type": "string"}, "name_fr": {"type": "string"},
                          "group": {"type": "string"}}),
        "unit": {"type": "string"}, "currency": {"type": "string"}, "price_type": {"const": "retail"},
        "eligible": {"type": "boolean"},
        "status": {"anyOf": [obj({"code": status, "level_vs_usual_pct": {"type": "integer"}, "month": month}),
                             {"type": "null"}]},  # null if not eligible
        "explanation": obj({"en": {"type": "string"}, "fr": {"type": "string"}}, required=[]),  # {} without forecast
        "reporting": obj({"months_reported_12": {"type": "integer", "minimum": 0, "maximum": 12},
                          "irregular": {"type": "boolean"}}),
        "signals": {"anyOf": [signals, {"type": "null"}]},
        "dates": obj({**common, "last_observed_month": month, "run_at": {"type": "string"}}),
        "history": {"type": "array", "items": obj({
            "month": month, "price": price, "flag": {"enum": [None, "data_error", "break", "unconfirmed_jump"]}})},
        "national_median": {"type": "array", "items": obj({"month": month, "price": price})},
        "forecast": {"type": "array", "maxItems": 5, "items": obj({
            "month": month, "step": {"type": "integer", "minimum": 1, "maximum": 5}, "horizon": horizon,
            "p025": price, "p10": price, "p50": price, "p90": price, "p975": price,
            "usual_level": price, "spike_threshold": price, "spike_probability": prob,
            "show_spike_probability": {"type": "boolean"}})},
        "attribution": attribution,
    }, title="food-price-watch export: series/<id>.json"),
    "track_record": obj({
        "schema_version": version, "model": {"type": "string"}, **common, "attribution": attribution,
        "backtest": obj({"period": {"type": "string"}, "population": {"type": "string"}, "method": {"type": "string"},
                         "by_horizon": {"type": "array", "items": track_row},
                         "by_country": {"type": "object",
                                        "additionalProperties": {"type": "array", "items": track_row}},
                         "by_reporting": obj({"regular": {"type": "array", "items": track_row},
                                              "irregular": {"type": "array", "items": track_row}}),
                         "irregular_definition": {"type": "string"}}),
        "live": obj({"by_horizon": {"type": "array", "items": track_row}, "note": {"type": "string"}}),
    }, title="food-price-watch export: track_record.json"),
}

# --- basket export (separate, optional; public_export/baskets/) ---
bversion = {"const": "basket-1.1"}
nmonth_ = {"type": ["string", "null"], "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}
bcommon = {"forecast_origin": nmonth_, "data_up_to": nmonth_}
component = {"enum": ["cereal", "pulses", "oil"]}
btrack_row = obj({"step": {"type": "integer", "minimum": 1, "maximum": 5}, "horizon": horizon,
                  "n": {"type": "integer", "minimum": 0}, "coverage80": prob, "coverage95": prob,
                  "typical_error_pct": {"type": ["integer", "null"]}})
SCHEMAS.update({
    "basket_manifest": obj({
        "schema_version": bversion, "status": {"enum": ["preview", "beta", "published"]},
        "generated_at": {"type": "string"}, **bcommon, "run_at": {"type": ["string", "null"]}, "model": {"type": "string"},
        "countries": {"type": "array", "items": country_id},
        "counts": obj({"baskets": {"type": "integer"}, "baskets_with_forecast": {"type": "integer"}}),
        "attribution": attribution, "attribution_fr": {"type": "string", "pattern": "Programme alimentaire mondial"},
        "license": obj({"data": {"type": "string"}, "url": {"type": "string"}}),
        "sources": {"type": "array", "items": {"type": "string"}}, "disclaimer": {"type": "string"},
        "disclaimer_fr": {"type": "string"},
        "files": {"type": "array", "items": obj({"path": {"type": "string"}, "bytes": {"type": "integer"},
                                                 "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})},
    }, title="food-price-watch basket export: manifest.json"),
    "basket_index": obj({
        "schema_version": bversion, **bcommon, "attribution": attribution,
        "baskets": {"type": "array", "items": obj({
            "id": {"type": "string"}, "market": {"type": "string"}, "eligible": {"type": "boolean"},
            "currency": {"type": "string"}, "components": {"type": "array", "items": component},
            "last_observed_month": month, "last_cost": price, "next_month": nmonth, "next_p10": nprice,
            "next_p50": nprice, "next_p90": nprice})},
    }, title="food-price-watch basket export: index/<country>.json"),
    "basket": obj({
        "schema_version": bversion, "id": {"type": "string"},
        "country": obj({"id": country_id, "name": {"type": "string"}}),
        "market": obj({"id": {"type": "integer"}, "name": {"type": "string"}}),
        "basket": obj({"basket_id": {"type": "string"}, "per": {"const": "person-month"},
                       "components": {"type": "array", "minItems": 1, "items": obj({
                           "component": component, "commodity": {"type": "string"}, "commodity_fr": {"type": "string"},
                           "quantity": {"type": "number", "exclusiveMinimum": 0}, "unit": {"type": "string"}})},
                       "missing": {"type": "array", "items": component}, "definition": {"type": "string"}}),
        "currency": {"type": "string"}, "eligible": {"type": "boolean"},
        "dates": obj({**bcommon, "last_observed_month": month, "run_at": {"type": ["string", "null"]}}),
        "history": {"type": "array", "items": obj({"month": month, "cost": price})},
        "forecast": {"type": "array", "maxItems": 5, "items": obj({
            "month": month, "step": {"type": "integer", "minimum": 1, "maximum": 5}, "horizon": horizon,
            "p025": price, "p10": price, "p50": price, "p90": price, "p975": price})},
        "explanation": obj({"en": {"type": "string"}, "fr": {"type": "string"}}),
        "attribution": attribution,
    }, title="food-price-watch basket export: basket/<id>.json"),
    "basket_track_record": obj({
        "schema_version": bversion, "model": {"type": "string"}, **bcommon, "attribution": attribution,
        "backtest": obj({"period": {"type": "string"}, "population": {"type": "string"},
                         "by_horizon": {"type": "array", "items": btrack_row},
                         "by_country": {"type": "object", "additionalProperties": {"type": "array", "items": btrack_row}}}),
        "live": obj({"by_horizon": {"type": "array", "items": btrack_row}}),
    }, title="food-price-watch basket export: track_record.json"),
})

if __name__ == "__main__":
    D.mkdir(parents=True, exist_ok=True)
    for name, schema in SCHEMAS.items():
        (D / f"{name}.schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {len(SCHEMAS)} schemas to {D}")
