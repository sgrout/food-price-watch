import numpy as np
import pandas as pd
import pytest

from fpw.basket import (basket_components, basket_cost_history, basket_id_of, load_baskets, load_conversions,
                        quantity_in)
from fpw.countries import COUNTRIES
from fpw.texts import COMMODITY_FR

CONV = load_conversions()


def test_config_files_are_valid_and_use_known_foods():
    b = load_baskets()
    assert set(b["country"]) == set(COUNTRIES)
    assert set(b["commodity"]) <= set(COMMODITY_FR)  # every basket food is a WFP name we export (and translate)
    for r in b.itertuples():  # every component can be priced per KG or L
        assert any(quantity_in(r.quantity, r.unit, u, r.component, CONV) > 0
                   for u in ["KG", "L"] if not CONV[(CONV.from_unit == r.unit) & (CONV.to_unit == u)].empty)


def test_oil_in_litres_priced_per_kg():
    assert quantity_in(0.75, "L", "KG", "oil", CONV) == pytest.approx(0.69)
    assert quantity_in(12, "KG", "100 KG", "cereal", CONV) == pytest.approx(0.12)
    with pytest.raises(ValueError):
        quantity_in(12, "KG", "L", "cereal", CONV)  # no density for cereals


def panel_rows(series_id, market_id, commodity, unit, prices, start=2020 * 12, suspect=None):
    m = start + np.arange(len(prices))
    sf = np.full(len(prices), np.nan)
    if suspect is not None:
        sf[suspect] = m[suspect] + 1
    return pd.DataFrame({"series_id": series_id, "country": "burundi", "market_id": market_id, "market": f"M{market_id}",
                         "series_commodity_id": 1, "commodity": commodity, "unit": unit, "m": m,
                         "lp": np.log(np.asarray(prices, dtype=float)), "suspect_from": sf})


BASKET = pd.DataFrame({"country": "burundi", "basket_id": "b1", "valid_from": "2026-10",
                       "component": ["cereal", "oil"], "commodity": ["Cassava flour", "Oil (palm)"],
                       "quantity": [12.0, 0.75], "unit": ["KG", "L"], "source": "", "note": ""})


def test_markets_need_every_component():
    panel = pd.concat([
        panel_rows("a", 1, "Cassava flour", "KG", [100] * 6), panel_rows("b", 1, "Oil (palm)", "KG", [1000] * 6),
        panel_rows("c", 2, "Cassava flour", "KG", [100] * 6),  # market 2 has no oil: no basket
    ], ignore_index=True)
    comps = basket_components(panel, BASKET, CONV)
    assert set(comps["market_id"]) == {1}
    assert comps.set_index("component").loc["oil", "quantity_in_series_unit"] == pytest.approx(0.69)


def test_cost_is_quantity_times_price_only_in_complete_months():
    panel = pd.concat([
        panel_rows("a", 1, "Cassava flour", "KG", [100, 110, 120, 130]),
        panel_rows("b", 1, "Oil (palm)", "KG", [1000, 1000, 1000, 1000], suspect=[2]),  # month 3: a data error
    ], ignore_index=True)
    panel = panel[~((panel["series_id"] == "a") & (panel["m"] == 2020 * 12 + 1))]  # month 2: no cereal price
    hist = basket_cost_history(panel, basket_components(panel, BASKET, CONV))
    assert list(hist["m"] - 2020 * 12) == [0, 3]  # months 2 and 3 are incomplete: no cost, nothing filled in
    assert hist["cost"].tolist() == pytest.approx([12 * 100 + 0.69 * 1000, 12 * 130 + 0.69 * 1000])
    assert set(hist["basket_series_id"]) == {basket_id_of("burundi", 1, "b1")} == {"burundi-1-basket-b1"}


def test_the_basket_unit_wins_over_other_units():
    panel = pd.concat([
        panel_rows("kg", 1, "Cassava flour", "KG", [100] * 3), panel_rows("bag", 1, "Cassava flour", "100 KG", [9000] * 9),
        panel_rows("b", 1, "Oil (palm)", "KG", [1000] * 3),
    ], ignore_index=True)
    comps = basket_components(panel, BASKET, CONV).set_index("component")
    assert comps.loc["cereal", "series_id"] == "kg"
