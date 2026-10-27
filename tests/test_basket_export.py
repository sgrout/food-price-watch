import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd
import pytest

from fpw.basket_export import build_basket_export
from fpw.basket_texts import composition_text, describe_basket, missing_components
from fpw.explain import display_price

SCHEMAS = Path(__file__).parents[1] / "export" / "schema"
ORIGIN = 2026 * 12 + 9


def inputs():
    comps = pd.DataFrame([
        {"basket_series_id": "burkina-faso-1-basket-ration_v1", "country": "burkina-faso", "basket_id": "ration_v1",
         "market_id": 1, "market": "Djibo", "component": "cereal", "commodity": "Millet", "series_id": "a",
         "series_unit": "KG", "quantity": 12.0, "unit": "KG", "quantity_in_series_unit": 12.0},
        {"basket_series_id": "burkina-faso-1-basket-ration_v1", "country": "burkina-faso", "basket_id": "ration_v1",
         "market_id": 1, "market": "Djibo", "component": "pulses", "commodity": "Beans (niebe)", "series_id": "b",
         "series_unit": "KG", "quantity": 1.8, "unit": "KG", "quantity_in_series_unit": 1.8},
        {"basket_series_id": "burkina-faso-2-basket-ration_v1", "country": "burkina-faso", "basket_id": "ration_v1",
         "market_id": 2, "market": "Kaya", "component": "cereal", "commodity": "Millet", "series_id": "c",
         "series_unit": "KG", "quantity": 12.0, "unit": "KG", "quantity_in_series_unit": 12.0},
        {"basket_series_id": "burkina-faso-2-basket-ration_v1", "country": "burkina-faso", "basket_id": "ration_v1",
         "market_id": 2, "market": "Kaya", "component": "pulses", "commodity": "Beans (niebe)", "series_id": "d",
         "series_unit": "KG", "quantity": 1.8, "unit": "KG", "quantity_in_series_unit": 1.8},
    ])
    months = np.arange(ORIGIN - 26, ORIGIN - 1)  # up to August 2026
    hist = pd.concat([pd.DataFrame({"basket_series_id": b, "country": "burkina-faso", "market_id": i, "market": n,
                                    "basket_id": "ration_v1", "m": months, "cost": 4000.0 + 10 * np.arange(len(months))})
                      for b, i, n in [("burkina-faso-1-basket-ration_v1", 1, "Djibo"),
                                      ("burkina-faso-2-basket-ration_v1", 2, "Kaya")]], ignore_index=True)
    lc = np.log(4300.0)
    fc = pd.DataFrame([{"series_id": "burkina-faso-1-basket-ration_v1", "model": "basket_copula", "origin": ORIGIN,
                        "step": s, "target": ORIGIN - 2 + s, "q025": lc - 0.3, "q10": lc - 0.12, "q50": lc,
                        "q90": lc + 0.14, "q975": lc + 0.3, "eligible_at_origin": True, "data_month": ORIGIN - 2,
                        "run_at": pd.Timestamp("2026-10-26 07:30")} for s in range(1, 6)])
    fc = pd.concat([fc, fc.assign(series_id="burkina-faso-2-basket-ration_v1", eligible_at_origin=False)])
    row = dict(population="eligible", model="basket_copula", split="holdout", n=500, coverage80=0.77,
               coverage95=0.93, median_abs_err=0.095)
    metrics = pd.DataFrame([{**row, "step": s} for s in range(1, 6)])
    metrics_country = metrics.assign(country="burkina-faso")
    return comps, hist, fc, metrics, metrics_country, pd.DataFrame()


@pytest.fixture(scope="module")
def files():
    return build_basket_export(*inputs(), generated_at=datetime(2026, 10, 26, 8, 30))


def load(files, p):
    return json.loads(files[p])


@pytest.mark.parametrize("name, path", [("basket_manifest", "manifest.json"), ("basket_index", "index/burkina-faso.json"),
                                        ("basket", "basket/burkina-faso-1-basket-ration_v1.json"),
                                        ("basket", "basket/burkina-faso-2-basket-ration_v1.json"),
                                        ("basket_track_record", "track_record.json")])
def test_files_match_their_schemas(files, name, path):
    jsonschema.validate(load(files, path), json.loads((SCHEMAS / f"{name}.schema.json").read_text()))


def test_basket_with_forecast(files):
    b = load(files, "basket/burkina-faso-1-basket-ration_v1.json")
    assert b["eligible"] and len(b["forecast"]) == 5 and b["basket"]["missing"] == ["oil"]
    nxt = b["forecast"][2]
    assert nxt["month"] == "2026-11" and nxt["p10"] < nxt["p50"] == 4300.0 < nxt["p90"]
    en, fr = b["explanation"]["en"], b["explanation"]["fr"]
    assert en.startswith("A staple basket for one person for one month (12 kg Millet, 1.8 kg Beans (niebe)) cost about")
    assert "Not included: cooking oil" in en and "not an official minimum expenditure basket" in en
    assert fr.startswith("Un panier de base pour une personne pendant un mois (12 kg Mil, 1,8 kg Niébé)")
    assert "Novembre 2026 : probablement entre" in fr and "Non inclus : huile" in fr


def test_basket_without_eligible_items_has_history_but_no_forecast(files):
    b = load(files, "basket/burkina-faso-2-basket-ration_v1.json")
    assert not b["eligible"] and b["forecast"] == [] and len(b["history"]) == 25
    assert "most likely" not in b["explanation"]["en"]


def test_manifest_hashes_and_track_record(files):
    m = load(files, "manifest.json")
    assert {f["path"] for f in m["files"]} == set(files) - {"manifest.json"}
    for f in m["files"]:
        assert f["sha256"] == hashlib.sha256(files[f["path"]]).hexdigest()
    assert m["counts"] == {"baskets": 2, "baskets_with_forecast": 1} and m["status"] == "beta"
    t = load(files, "track_record.json")["backtest"]
    assert t["by_horizon"][2]["typical_error_pct"] == 10 and set(t["by_country"]) == {"burkina-faso"}


def test_basket_text_numbers_come_from_facts():
    comps = [{"component": "cereal", "commodity": "Cassava flour", "quantity": 12.0, "unit": "KG"},
             {"component": "oil", "commodity": "Oil (palm)", "quantity": 0.75, "unit": "L"}]
    f = {"components": comps, "currency": "BIF", "last_month": ORIGIN - 2, "cost": 30104.96, "next_month": ORIGIN + 1,
         "next_lo": 27650.5, "next_hi": 33120.25, "last_fc_month": ORIGIN + 3, "last_lo": 26000.0, "last_hi": 36500.75}
    for lang in ("en", "fr"):
        text = describe_basket(f, lang)
        allowed = {display_price(f[k], lang) for k in ["cost", "next_lo", "next_hi", "last_lo", "last_hi"]}
        allowed |= {"12", "0.75", "0,75", "8", "10", "2026", "2027"}
        numbers = set(re.findall(r"\d(?:[\d,. ]*\d)?", text))
        assert numbers <= allowed, (lang, numbers - allowed)
    assert missing_components(comps) == ["pulses"]
    assert composition_text(comps, "fr") == "12 kg Farine de manioc, 0,75 l Huile de palme"


BSAMPLE = SCHEMAS.parent / "sample-baskets"


@pytest.mark.parametrize("path", sorted(p.relative_to(BSAMPLE).as_posix() for p in BSAMPLE.rglob("*.json")))
def test_committed_basket_sample_matches_schemas_and_manifest(path):
    name = "basket" if path.startswith("basket/") else "basket_index" if path.startswith("index/") else "basket_" + path[:-5]
    doc = json.loads((BSAMPLE / path).read_text())
    jsonschema.validate(doc, json.loads((SCHEMAS / f"{name}.schema.json").read_text()))
    if path == "manifest.json":
        for f in doc["files"]:
            assert hashlib.sha256((BSAMPLE / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]


def test_months_after_data_up_to_are_history_only_and_baskets_follow_the_item_export():
    comps, hist, fc, metrics, metrics_country, live = inputs()
    late = hist[hist["m"] == ORIGIN - 2].assign(m=ORIGIN - 1, cost=9999.0)  # September, published early
    hist = pd.concat([hist, late], ignore_index=True)
    files = build_basket_export(comps, hist, fc, metrics, metrics_country, live, generated_at=datetime(2026, 10, 26),
                                item_series={"a", "b"})  # market 2's foods are not in the item export
    assert set(files) == {"manifest.json", "index/burkina-faso.json", "basket/burkina-faso-1-basket-ration_v1.json",
                          "track_record.json"}
    b = load(files, "basket/burkina-faso-1-basket-ration_v1.json")
    assert b["history"][-1] == {"month": "2026-09", "cost": 9999.0}  # kept, as in the item export
    assert b["dates"]["last_observed_month"] == b["dates"]["data_up_to"] == "2026-08"
    assert "in August 2026" in b["explanation"]["en"] and "9,999" not in b["explanation"]["en"]
    assert load(files, "index/burkina-faso.json")["baskets"][0]["last_observed_month"] == "2026-08"
