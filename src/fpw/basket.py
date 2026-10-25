"""Food-basket cost per market: the basket definition (versioned data in config/) and its historical cost.

A basket is a list of components (WFP commodity, quantity, unit) per country; see config/baskets.csv. It is ours
(ration-based), not an official minimum expenditure basket. A market has a basket only if every component has a
retail series there; a month has a cost only if every component was observed that month (no filling), and known
data errors are not used. Costs are in local currency per person per month (nominal).
"""

from pathlib import Path

import numpy as np
import pandas as pd

CONFIG = Path(__file__).parents[2] / "config"
BASKET_COLUMNS = ["country", "basket_id", "valid_from", "component", "commodity", "quantity", "unit", "source", "note"]


def load_baskets(path: Path = CONFIG / "baskets.csv") -> pd.DataFrame:
    b = pd.read_csv(path, dtype={"valid_from": str}, keep_default_na=False)
    if list(b.columns) != BASKET_COLUMNS:
        raise ValueError(f"basket columns {list(b.columns)} != {BASKET_COLUMNS}")
    b["quantity"] = b["quantity"].astype(float)
    if (b["quantity"] <= 0).any():
        raise ValueError("basket quantities must be positive")
    if b.duplicated(["country", "basket_id", "component"]).any():
        raise ValueError("a component appears twice in a basket")
    return b


def load_conversions(path: Path = CONFIG / "unit_conversions.csv") -> pd.DataFrame:
    c = pd.read_csv(path, keep_default_na=False)
    c["factor"] = c["factor"].astype(float)
    return c


def quantity_in(quantity: float, unit: str, series_unit: str, component: str, conversions: pd.DataFrame) -> float:
    """The basket quantity expressed in the unit a series is priced in (e.g. 0.75 L of oil priced per KG -> 0.69)."""
    rows = conversions[(conversions["from_unit"] == unit) & (conversions["to_unit"] == series_unit)
                       & conversions["component"].isin([component, "*"])]
    if rows.empty:
        raise ValueError(f"no conversion {unit} -> {series_unit} for {component}")
    return quantity * float(rows["factor"].iloc[0])


def basket_components(panel: pd.DataFrame, baskets: pd.DataFrame, conversions: pd.DataFrame) -> pd.DataFrame:
    """One row per (market, component): the series used and the quantity in that series' unit. Markets without a
    series for every component of their country's basket are left out. If a market has several units for a
    commodity, the basket's own unit wins, then the series with the longest history."""
    series = panel.groupby("series_id").agg(country=("country", "first"), market_id=("market_id", "first"),
                                            market=("market", "first"), commodity=("commodity", "first"),
                                            unit=("unit", "first"), n=("m", "size")).reset_index()
    rows = []
    for (country, basket_id), b in baskets.groupby(["country", "basket_id"]):
        s = series[series["country"] == country]
        for market_id, ms in s.groupby("market_id"):
            picked = []
            for comp in b.itertuples():
                cand = ms[ms["commodity"] == comp.commodity]
                cand = cand.assign(own=cand["unit"] == comp.unit).sort_values(["own", "n"], ascending=False)
                ok = []
                for c in cand.itertuples():
                    try:
                        ok.append((c, quantity_in(comp.quantity, comp.unit, c.unit, comp.component, conversions)))
                    except ValueError:
                        continue
                if not ok:
                    break
                c, q = ok[0]
                picked.append({"country": country, "basket_id": basket_id, "market_id": int(market_id),
                               "market": c.market, "component": comp.component, "commodity": comp.commodity,
                               "series_id": c.series_id, "series_unit": c.unit, "quantity": comp.quantity,
                               "unit": comp.unit, "quantity_in_series_unit": q})
            if len(picked) == len(b):
                rows.extend(picked)
    return pd.DataFrame(rows)


def basket_id_of(country: str, market_id: int, basket_id: str) -> str:
    return f"{country}-{int(market_id)}-basket-{basket_id}"


def basket_cost_history(panel: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    """Monthly basket cost per market: sum of quantity x price over the components, only in months where every
    component has a price that is not a known data error. Columns: basket_series_id, country, market_id, market,
    basket_id, m, cost, and one price column per component."""
    clean = panel[panel["suspect_from"].isna()] if "suspect_from" in panel else panel
    out = []
    for (country, market_id, basket_id), comps in components.groupby(["country", "market_id", "basket_id"]):
        wide = None
        for c in comps.itertuples():
            p = clean.loc[clean["series_id"] == c.series_id, ["m", "lp"]]
            p = p.assign(**{f"price_{c.component}": np.exp(p["lp"]),
                            f"cost_{c.component}": np.exp(p["lp"]) * c.quantity_in_series_unit}).drop(columns="lp")
            wide = p if wide is None else wide.merge(p, on="m", how="inner")
        if wide is None or wide.empty:
            continue
        cost_cols = [f"cost_{c}" for c in comps["component"]]
        wide["cost"] = wide[cost_cols].sum(axis=1)
        out.append(wide.drop(columns=cost_cols).assign(
            basket_series_id=basket_id_of(country, market_id, basket_id), country=country, market_id=int(market_id),
            market=comps["market"].iloc[0], basket_id=basket_id))
    cols = ["basket_series_id", "country", "market_id", "market", "basket_id", "m", "cost"]
    if not out:
        return pd.DataFrame(columns=cols)
    res = pd.concat(out, ignore_index=True)
    return res[cols + [c for c in res.columns if c not in cols]].sort_values(["basket_series_id", "m"]) \
        .reset_index(drop=True)
