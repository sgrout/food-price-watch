from datetime import date

import pandas as pd


def prices(rows, country="mali", market_id=1, commodity="Maize", commodity_id=51, pricetype="Retail", unit="KG",
           currency="XOF", priceflag="actual") -> pd.DataFrame:
    """Tiny silver-like price frame from (yyyy-mm, price) pairs: one series unless overridden per row via dicts."""
    out = []
    for r in rows:
        r = dict(zip(["month", "price"], r)) if not isinstance(r, dict) else r
        y, m = map(int, r["month"].split("-"))
        out.append({
            "country": r.get("country", country), "market_id": r.get("market_id", market_id),
            "market": f"M{r.get('market_id', market_id)}", "commodity": r.get("commodity", commodity),
            "commodity_id": r.get("commodity_id", commodity_id),
            "series_commodity_id": r.get("commodity_id", commodity_id), "category": "cereals and tubers",
            "pricetype": r.get("pricetype", pricetype), "unit": r.get("unit", unit), "date": date(y, m, 15),
            "currency": r.get("currency", currency), "priceflag": r.get("priceflag", priceflag),
            "price": r["price"], "usdprice": r["price"] / 600,
        })
    return pd.DataFrame(out)


def months(start: str, values) -> list[tuple[str, float]]:
    """Consecutive months from start (yyyy-mm) with the given values."""
    periods = pd.period_range(start, periods=len(values), freq="M")
    return [(str(p), v) for p, v in zip(periods, values)]
