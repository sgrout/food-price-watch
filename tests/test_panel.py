import numpy as np
import pandas as pd

from fpw.backtest import walk_forward
from fpw.baselines import naive
from fpw.panel import month_date, month_index, monthly_panel
from fpw.quality import flag_suspects
from fpw.silver import link_continuations
from helpers import months, prices


def test_month_index_round_trip():
    m = month_index(["2024-01-15", "2024-12-15"])
    assert list(m % 12) == [0, 11] and month_date(m.iloc[1]).isoformat() == "2024-12-15"


def test_panel_keeps_series_identity_and_drops_suspect_and_non_staples():
    df = pd.concat([
        prices(months("2020-01", [100, 100, 500, 100]), market_id=7),  # one spike_revert
        prices(months("2020-01", [100] * 4), market_id=7, commodity="Livestock (goat)", commodity_id=9),
        prices(months("2020-01", [100] * 4), market_id=7, pricetype="Wholesale"),
    ], ignore_index=True)
    p = monthly_panel(flag_suspects(df))
    assert p["series_id"].nunique() == 1 and len(p) == 3
    row = p.iloc[0]
    assert (row["country"], row["market_id"], row["series_commodity_id"], row["unit"]) == ("mali", 7, 51, "KG")
    assert np.isclose(p["lp"].iloc[0], np.log(100))


def test_linked_commodity_is_one_series_with_its_newest_name():
    df = pd.concat([
        prices(months("2025-09", [100] * 3), country="burundi", currency="BIF", commodity="Beans", commodity_id=50),
        prices(months("2025-12", [98] * 3), country="burundi", currency="BIF", commodity="Beans (haricot, yellow)",
               commodity_id=829),
    ], ignore_index=True).drop(columns="series_commodity_id")
    p = monthly_panel(flag_suspects(link_continuations(df, {("burundi", 50): 829})))
    assert p["series_id"].nunique() == 1 and len(p) == 6
    assert set(p["commodity"]) == {"Beans (haricot, yellow)"} and set(p["series_commodity_id"]) == {829}


def test_forecast_rows_can_be_grouped_by_market():
    """Basket preparation: every forecast row carries market_id, series_commodity_id and unit."""
    df = pd.concat([prices(months("2018-01", 100 + np.arange(60) % 12), market_id=3, commodity=c, commodity_id=i)
                    for c, i in [("Maize", 51), ("Millet", 73)]], ignore_index=True)
    p = monthly_panel(flag_suspects(df))
    fc = walk_forward(p, [p["m"].max() - 3], models={"naive": naive})
    assert set(fc["market_id"]) == {3} and set(fc["series_commodity_id"]) == {51, 73} and set(fc["unit"]) == {"KG"}
    assert fc.groupby(["market_id", "origin", "step"]).size().eq(2).all()  # both foods of the market, per case
