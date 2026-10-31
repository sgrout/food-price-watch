"""Plain-language explanation of a live forecast, produced by code from the model inputs (no LLM).

`facts()` computes every number that may appear; `describe()` only formats those facts with fpw.texts templates.

Display rule (shared with the public site, docs/export-contract.md section 3): numbers are first rounded to the
precision the export publishes (prices 2 decimals, probabilities 3 decimals), then displayed with round-half-even:
prices with 0 decimals from 100, 1 decimal from 10 to 100, 2 decimals below 10; percentages as whole numbers of
100 x the exported probability. Half-even is applied to the exact decimal value (94.55 -> 94.6), not to the binary
float (which is 94.5499...). So a text and a page formatted from the same export always show the same number.
"""

import numpy as np
import pandas as pd

from decimal import ROUND_HALF_EVEN, Decimal

from fpw.backtest import LAG
from fpw.texts import GROUPS, IN_COUNTRY, MONTHS, NUMBER_FORMAT, TEXTS

FLAT_PCT = 2  # changes below this (in %) are described as "about stable"
STATUS_THRESHOLDS = [(2.0, "crisis"), (1.0, "alert"), (0.25, "stress")]  # ALPS-style, on z
NEXT_STEP, LAST_STEP = 3, 5  # steps 3 and 5 = next month and three months ahead (see fpw.backtest)


def status(z: float) -> str:
    return next((name for limit, name in STATUS_THRESHOLDS if z >= limit), "normal")


def _pct(log_change: float) -> int:
    return int(round(100 * (np.exp(log_change) - 1)))


def facts(rows: pd.DataFrame, currency: str) -> dict:
    """Facts for one series at one origin from its calibrated forecast rows (one per step, with case features)."""
    by_step = rows.set_index("step")
    first = rows.iloc[0]
    nxt, last = by_step.loc[NEXT_STEP], by_step.loc[LAST_STEP]
    return {
        "data_month": int(first["m_last"]), "data_up_to": int(first.get("reference_month", int(first["origin"]) - LAG)),
        "months_ahead": int(nxt["target"]) - int(first["m_last"]), "status": status(float(first["z_now"])),
        "level_pct": _pct(float(first["resid_last"])),
        "trend_pct": _pct(float(first["ret3"])) if pd.notna(first["ret3"]) else None,
        "market_pct": _pct(float(first["grp_ret3"])) if pd.notna(first["grp_ret3"]) else None,
        "market_n": int(first["grp_n"]), "group": first["commodity_group"], "country": first["country"],
        # exported precision (fpw.export): prices 2 decimals, probabilities 3 decimals
        "next_month": int(nxt["target"]), "next_lo": export_price(np.exp(nxt["q10"])),
        "next_hi": export_price(np.exp(nxt["q90"])), "next_spike": export_prob(nxt["spike_prob"]),
        "last_month": int(last["target"]), "last_lo": export_price(np.exp(last["q10"])),
        "last_hi": export_price(np.exp(last["q90"])), "last_spike": export_prob(last["spike_prob"]),
        "currency": currency, "unit": first["unit"],
    }


def export_price(x) -> float:
    return round(float(x), 2)


def export_prob(x) -> float:
    return round(float(x), 3)


def _decimal_half_even(x: float, decimals: int) -> Decimal:
    """Half-even on the exact decimal value as exported (str(94.55) = '94.55'), not on the binary float."""
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN)


def _group_thousands(digits: str, sep: str) -> str:
    out = ""
    while len(digits) > 3:
        digits, out = digits[:-3], sep + digits[-3:] + out
    return digits + out


def display_price(x: float, lang: str = "en") -> str:
    """0 decimals from 100, 1 decimal from 10 to 100, 2 below 10; half-even; locale separators."""
    decimals = 0 if x >= 100 else 1 if x >= 10 else 2
    sep, mark = NUMBER_FORMAT[lang]
    whole, _, frac = f"{_decimal_half_even(x, decimals):f}".partition(".")
    return _group_thousands(whole, sep) + (mark + frac if frac else "")


def display_pct(p: float) -> str:
    """A probability as a whole percentage of the exported value, half-even (0.125 -> 12, 0.135 -> 14)."""
    return str(int(_decimal_half_even(Decimal(str(p)) * 100, 0)))


def _signed(t: dict, key: str, pct: int | None, **kw) -> str | None:
    if pct is None:
        return None
    if abs(pct) < FLAT_PCT:
        return t[f"{key}_flat"].format(**kw)
    return t[f"{key}_up" if pct > 0 else f"{key}_down"].format(pct=abs(pct), **kw)


def describe(f: dict, lang: str = "en") -> str:
    t, months = TEXTS[lang], MONTHS[lang]
    month = lambda m: f"{months[m % 12]} {m // 12}"
    cap = lambda s: s[:1].upper() + s[1:]  # sentence start ("Novembre 2026 :")
    price = lambda x: display_price(x, lang)
    st = t[f"status_{f['status']}"]
    if abs(f["level_pct"]) < FLAT_PCT:
        level = t["level_at"].format(month=month(f["data_month"]), status=st)
    else:
        key = "level_above" if f["level_pct"] > 0 else "level_below"
        level = t[key].format(month=month(f["data_month"]), pct=abs(f["level_pct"]), status=st)
    parts = [
        level,
        _signed(t, "trend", f["trend_pct"]),
        _signed(t, "market", f["market_pct"], n=f["market_n"], group=GROUPS[lang].get(f["group"], GROUPS[lang]["other"]),
                in_country=IN_COUNTRY[lang][f["country"]])
        if f["market_n"] > 1 else None,
        t["stale"].format(month=month(f["data_month"]), next=month(f["next_month"]), k=f["months_ahead"])
        if f["data_month"] < f.get("data_up_to", f["data_month"]) else None,
        t["forecast"].format(Month=cap(month(f["next_month"])), lo=price(f["next_lo"]), hi=price(f["next_hi"]),
                             currency=f["currency"], unit=f["unit"]),
        t["forecast"].format(Month=cap(month(f["last_month"])), lo=price(f["last_lo"]), hi=price(f["last_hi"]),
                             currency=f["currency"], unit=f["unit"]),
        t["spike"].format(month=month(f["next_month"]), p=display_pct(f["next_spike"])),
        t["caveat"],
    ]
    return " ".join(p for p in parts if p)
