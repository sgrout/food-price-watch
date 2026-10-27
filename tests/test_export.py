import csv
import hashlib
import io
import json
import tarfile
from datetime import datetime
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd
import pytest

from fpw.export import (HORIZONS, SPIKE_STEP, build_export, month_str, series_slug, skill_verdict, to_tarball)

SCHEMAS = Path(__file__).parents[1] / "export" / "schema"
ORIGIN = 2026 * 12 + 9  # October 2026
RUN = pd.Timestamp("2026-10-26 06:00")


def inputs():
    base = dict(country="mali", series_commodity_id=51, unit="KG", commodity="Maize", commodity_group="maize",
                currency="XOF", origin=ORIGIN, data_month=ORIGIN - 2, last_obs_month=ORIGIN - 2, model_version="1",
                run_at=RUN, level_pct=21, status="stress", explanation="In August 2026 the price was 21% above ...",
                explanation_fr="En août 2026, le prix était 21\u202f% au-dessus ...", months_reported_12=12)
    summary = pd.DataFrame([
        {**base, "series_id": "mali|247|51|Retail|KG", "market_id": 247, "market": "Bamako", "eligible_at_origin": True},
        {**base, "series_id": "mali|300|51|Retail|KG", "market_id": 300, "market": "Kita", "eligible_at_origin": False,
         "status": "normal", "level_pct": -3, "months_reported_12": 5, "commodity": "Sesame"},
    ])
    lp = np.log(200.0)
    forecasts = pd.DataFrame([{
        "series_id": "mali|247|51|Retail|KG", "step": s, "target": ORIGIN - 2 + s, "q025": lp - 0.3, "q10": lp - 0.15,
        "q50": lp, "q90": lp + 0.15, "q975": lp + 0.3, "spike_prob": 0.2 + 0.01 * s, "expected": lp - 0.1,
        "sigma": 0.12} for s in range(1, 6)])
    months = pd.date_range("2022-01-15", "2026-08-15", freq="MS") + pd.Timedelta(days=14)
    prices = pd.concat([pd.DataFrame({
        "country": "mali", "market_id": mid, "series_commodity_id": 51, "unit": "KG", "date": months.date,
        "price": 190.0 + np.arange(len(months)), "is_suspect": False, "quality_flag": None,
        "admin1": "Bamako" if mid == 247 else "Kayes", "admin2": "x", "latitude": 12.65, "longitude": -8.0})
        for mid in (247, 300)], ignore_index=True)
    prices.loc[5, ["is_suspect", "quality_flag"]] = True, "spike_revert"
    metric_row = dict(population="eligible", model="lgbm_cal", split="holdout", n=100, coverage80=0.77,
                      coverage95=0.94, median_abs_err=0.095, onset_brier=0.109, onset_brier_climatology=0.114)
    metrics = pd.DataFrame([{**metric_row, "step": s} for s in range(1, 6)]
                           + [{**metric_row, "step": 1, "model": "naive"}]
                           + [{**metric_row, "step": s, "population": "eligible_irregular", "coverage80": 0.68}
                              for s in range(1, 6)]
                           + [{**metric_row, "step": s, "population": "eligible_regular"} for s in range(1, 6)])
    metrics_country = pd.DataFrame([{**metric_row, "step": s, "country": "mali"} for s in range(1, 6)])
    return summary, forecasts, prices, metrics, metrics_country, pd.DataFrame()


@pytest.fixture(scope="module")
def files():
    return build_export(*inputs(), generated_at=datetime(2026, 10, 26, 7, 30))


def load(files, path):
    return json.loads(files[path])


@pytest.mark.parametrize("name, path", [("manifest", "manifest.json"), ("index", "index.json"),
                                        ("index", "index/mali.json"),
                                        ("countries", "countries.json"), ("track_record", "track_record.json"),
                                        ("series", "series/mali-247-51-retail-kg.json"),
                                        ("series", "series/mali-300-51-retail-kg.json")])
def test_every_file_matches_its_schema(files, name, path):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    jsonschema.validate(load(files, path), schema)


def test_ids_and_months():
    assert series_slug("burkina-faso", 12, 829, "100 KG") == "burkina-faso-12-829-retail-100-kg"
    assert month_str(ORIGIN) == "2026-10" and month_str(2026 * 12) == "2026-01"


def test_manifest_lists_every_file_with_its_hash(files):
    m = load(files, "manifest.json")
    listed = {f["path"]: f for f in m["files"]}
    assert set(listed) == set(files) - {"manifest.json"}
    for path, f in listed.items():
        assert f["bytes"] == len(files[path]) and f["sha256"] == hashlib.sha256(files[path]).hexdigest()
    assert m["status"] == "preview" and m["forecast_origin"] == "2026-10" and m["data_up_to"] == "2026-08"


def test_series_with_forecast(files):
    s = load(files, "series/mali-247-51-retail-kg.json")
    assert s["eligible"] and len(s["forecast"]) == 5 and s["explanation"]["en"].startswith("In August")
    assert [f["horizon"] for f in s["forecast"]] == list(HORIZONS.values())
    nxt = s["forecast"][SPIKE_STEP - 1]
    assert nxt["p10"] < nxt["p50"] < nxt["p90"] and nxt["p50"] == 200.0 and nxt["month"] == "2026-11"
    # spike chance only for next month (further out, new-spike warnings are worse than the base rate)
    assert [f["spike_probability"] is not None for f in s["forecast"]] == [False, False, True, False, False]
    assert s["history"][5]["flag"] == "data_error" and s["history"][-1]["month"] == "2026-08"
    assert s["market"]["admin1"] == "Bamako" and s["market"]["latitude"] == 12.65


def test_series_without_enough_data_has_history_but_no_forecast_and_no_status(files):
    s = load(files, "series/mali-300-51-retail-kg.json")
    assert not s["eligible"] and s["forecast"] == [] and s["explanation"] == {} and len(s["history"]) > 0
    assert s["status"] is None  # the usual level of a series without enough data is not reliable
    row = next(r for r in load(files, "index.json")["series"] if r["id"] == "mali-300-51-retail-kg")
    assert row["status"] is None


def test_index_countries_and_track_record(files):
    idx = load(files, "index.json")["series"]
    assert [r["eligible"] for r in idx] == [True, False] and idx[0]["next_spike_probability"] == 0.23
    c = load(files, "countries.json")["countries"][0]
    assert c["series"] == 2 and c["series_with_forecast"] == 1 and c["status_counts"]["stress"] == 1
    t = load(files, "track_record.json")
    assert len(t["backtest"]["by_horizon"]) == 5 and t["backtest"]["by_horizon"][2]["typical_error_pct"] == 10
    assert t["backtest"]["by_horizon"][2]["new_spike_verdict"] == "better"  # 0.109 vs 0.114: -4.4 %
    assert t["live"]["by_horizon"] == [] and set(t["backtest"]["by_country"]) == {"mali"}


def test_csv_download(files):
    path = next(p for p in files if p.startswith("downloads/forecasts_"))
    assert path == "downloads/forecasts_2026-10-26.csv"
    rows = list(csv.DictReader(io.StringIO(files[path].decode())))
    assert len(rows) == 5 and {r["series_id"] for r in rows} == {"mali-247-51-retail-kg"}
    assert [r["spike_probability"] != "" for r in rows] == [False, False, True, False, False]
    assert "World Food Programme" in files["downloads/README.txt"].decode()


def test_every_json_file_carries_the_attribution(files):
    for path, b in files.items():
        if path.endswith(".json"):
            assert "World Food Programme" in json.loads(b)["attribution"], path


def test_tarball_round_trip_and_is_reproducible(files):
    tar = to_tarball(files)
    assert tar == to_tarball(dict(reversed(list(files.items()))))
    with tarfile.open(fileobj=io.BytesIO(tar), mode="r:gz") as t:
        assert sorted(t.getnames()) == sorted(files)
        assert t.extractfile("manifest.json").read() == files["manifest.json"]


def test_app_verdict_mirrors_the_export():
    from strings import skill_verdict as app_verdict
    words = {"better": "better than the base rate", "no_better": "no better than the base rate",
             "worse": "worse than the base rate"}
    for a, b in [(0.0985, 0.112), (0.110, 0.112), (0.1544, 0.1347), (0.5, 0.5)]:
        assert app_verdict(a, b) == words[skill_verdict(a, b)]


def test_committed_schemas_are_up_to_date_with_the_generator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("export_schemas", SCHEMAS.parents[1] / "scripts" / "export_schemas.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    for name, schema in gen.SCHEMAS.items():
        assert json.loads((SCHEMAS / f"{name}.schema.json").read_text()) == schema, name


SAMPLE = SCHEMAS.parent / "sample"


@pytest.mark.parametrize("path", sorted(p.relative_to(SAMPLE).as_posix() for p in SAMPLE.rglob("*.json")))
def test_committed_sample_matches_the_schemas_and_its_manifest(path):
    """The sample the site is built against must follow the same contract as the real export."""
    name = "series" if path.startswith("series/") else "index" if path.startswith("index") else path[:-5]
    doc = json.loads((SAMPLE / path).read_text())
    jsonschema.validate(doc, json.loads((SCHEMAS / f"{name}.schema.json").read_text()))
    if path == "manifest.json":
        for f in doc["files"]:
            assert hashlib.sha256((SAMPLE / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]


def test_french_names_texts_and_reporting(files):
    s = load(files, "series/mali-247-51-retail-kg.json")
    assert s["commodity"]["name_fr"] == "Maïs" and s["explanation"]["fr"].startswith("En août 2026")
    assert s["reporting"] == {"months_reported_12": 12, "irregular": False}
    k = load(files, "series/mali-300-51-retail-kg.json")
    assert k["reporting"] == {"months_reported_12": 5, "irregular": True}  # fewer than 9 of 12
    assert k["commodity"]["name_fr"] == "Sesame"  # no translation: falls back to English ...
    m = load(files, "manifest.json")
    assert m["missing_translations"] == ["Sesame"]  # ... and is listed, so it gets added
    assert "Programme alimentaire mondial" in m["attribution_fr"]
    idx = {r["id"]: r for r in load(files, "index.json")["series"]}
    assert idx["mali-300-51-retail-kg"]["irregular_reporting"] and idx["mali-247-51-retail-kg"]["commodity_fr"] == "Maïs"
    t = load(files, "track_record.json")["backtest"]
    assert t["by_reporting"]["irregular"][2]["coverage80"] == 0.68 and len(t["by_reporting"]["regular"]) == 5
    assert "fewer than 9 of the last 12 months" in t["irregular_definition"]
    assert "Prévisions Staple Signals" in files["downloads/README.txt"].decode()


def test_every_wfp_commodity_in_the_sample_has_a_french_name():
    from fpw.texts import COMMODITY_FR
    names = {r["commodity"] for r in json.loads((SAMPLE / "index.json").read_text())["series"]}
    assert names <= set(COMMODITY_FR)


def test_status_must_be_known_and_beta_is_valid():
    files = build_export(*inputs(), generated_at=datetime(2026, 10, 26), status="beta")
    m = json.loads(files["manifest.json"])
    jsonschema.validate(m, json.loads((SCHEMAS / "manifest.schema.json").read_text()))
    assert m["status"] == "beta"
    with pytest.raises(ValueError):
        build_export(*inputs(), generated_at=datetime(2026, 10, 26), status="live")


def test_signals_and_silent_series_in_the_export():
    from fpw.panel import monthly_panel
    from fpw.signals import compute_signals, silent_series
    summary, forecasts, prices, metrics, metrics_country, live = inputs()
    months = pd.date_range("2022-01-15", "2026-08-15", freq="MS") + pd.Timedelta(days=14)
    others = [pd.DataFrame({"country": "mali", "market_id": mid, "series_commodity_id": 51, "unit": "KG",
                            "date": months.date, "price": 190.0 + np.arange(len(months)), "is_suspect": False,
                            "quality_flag": None, "admin1": "Mopti", "admin2": "x", "latitude": 14.5, "longitude": -4.2})
              for mid in (301, 302, 303, 304)]
    quiet = others[-1].assign(market_id=400)
    quiet = quiet[quiet["date"] < pd.Timestamp("2026-05-15").date()]  # last price April 2026
    p = pd.concat([prices] + others + [quiet], ignore_index=True)
    p.loc[(p["market_id"] == 247) & (p["date"] == months[-1].date()), "price"] = 400.0  # Bamako: far above now
    p = p.assign(pricetype="Retail", commodity="Maize", market="M" + p["market_id"].astype(str),
                 confirmed_date=p["date"])
    p.loc[p["market_id"] == 400, "market"] = "Tenenkou"
    panel = monthly_panel(p)
    sig = compute_signals(panel, ORIGIN - 2)
    extra = silent_series(panel, sig, set(summary["series_id"]))
    assert extra["series_id"].tolist() == ["mali|400|51|Retail|KG"]
    files = build_export(summary, forecasts, p, metrics, metrics_country, live, generated_at=datetime(2026, 10, 26),
                         signals=sig, silent=extra)
    for name, path in [("series", "series/mali-247-51-retail-kg.json"), ("series", "series/mali-400-51-retail-kg.json"),
                       ("index", "index.json"), ("countries", "countries.json")]:
        jsonschema.validate(load(files, path), json.loads((SCHEMAS / f"{name}.schema.json").read_text()))
    bamako = load(files, "series/mali-247-51-retail-kg.json")
    g = bamako["signals"]["national_gap"]
    assert g["month"] == "2026-08" and g["n_markets"] == 6 and g["pct"] > 25 and g["far_above_usual"]
    assert bamako["signals"]["text"]["en"].startswith("In August 2026 the price here was")
    assert bamako["national_median"][-1]["month"] == "2026-08" and len(bamako["national_median"]) == 36
    t = load(files, "series/mali-400-51-retail-kg.json")
    assert not t["eligible"] and t["status"] is None and t["forecast"] == [] and t["history"][-1]["month"] == "2026-04"
    assert t["signals"]["silence"] == {"months": 4, "last_reported_month": "2026-04", "reference_month": "2026-08"}
    assert t["signals"]["national_gap"] is None and "since April 2026" in t["signals"]["text"]["en"]
    mali = load(files, "countries.json")["countries"][0]
    assert mali["silent_markets"] == [{"market_id": 400, "market": "Tenenkou", "admin1": "Mopti", "months": 4,
                                       "last_reported_month": "2026-04"}]
    assert mali["reference_month"] == "2026-08" and mali["far_above_usual"] == 1
    row = next(r for r in load(files, "index.json")["series"] if r["id"] == "mali-400-51-retail-kg")
    assert row["silent_months"] == 4 and row["gap_pct"] is None
