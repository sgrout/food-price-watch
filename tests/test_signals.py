import numpy as np
import pandas as pd
import pytest

from fpw.signals import (compute_signals, market_silence, national_medians, reference_months, series_gaps,
                         silent_series)

AUG = 2026 * 12 + 7  # August 2026 = data_up_to


def panel(markets: dict, commodity_id=1, unit="KG", country="mali", start=AUG - 47):
    """markets: {market_id: prices from `start`, None = no price that month}."""
    rows = []
    for mid, prices in markets.items():
        for i, x in enumerate(prices):
            if x is not None:
                rows.append({"series_id": f"{country}|{mid}|{commodity_id}|Retail|{unit}", "country": country,
                             "market_id": mid, "series_commodity_id": commodity_id, "commodity": "Millet",
                             "market": f"M{mid}", "unit": unit, "m": start + i, "lp": np.log(x), "suspect_from": np.nan})
    return pd.DataFrame(rows)


def full(price=100.0, n=48):
    return [price] * n


def test_late_publication_is_not_silence():
    # August is not yet published for most markets: the reference month is July and nobody is silent
    p = panel({i: full()[:-1] + [None] for i in range(1, 9)} | {9: full()})
    ref = reference_months(p, AUG)
    assert ref["mali"] == AUG - 1
    assert not market_silence(p, AUG, ref)["silent"].any()


def test_one_early_month_does_not_make_others_silent():
    early = {i: full() for i in range(1, 9)}
    p = panel(early | {9: full() + [100.0]})  # market 9 also has September (after data_up_to)
    ref = reference_months(p, AUG)
    assert ref["mali"] == AUG
    assert not market_silence(p, AUG, ref)["silent"].any()


def test_market_silent_for_two_months_is_listed():
    p = panel({i: full() for i in range(1, 9)} | {9: full()[:-2] + [None, None], 10: full()[:-1] + [None]})
    s = market_silence(p, AUG, reference_months(p, AUG)).set_index("market_id")
    assert s.loc[9, "months"] == 2 and s.loc[9, "silent"] and s.loc[9, "listed"]
    assert s.loc[10, "months"] == 1 and not s.loc[10, "silent"]


def test_long_dead_and_short_markets_are_not_listed():
    p = panel({i: full() for i in range(1, 9)} | {9: full()[:20] + [None] * 28, 10: [None] * 40 + [100.0] * 5 + [None] * 3})
    s = market_silence(p, AUG, reference_months(p, AUG)).set_index("market_id")
    assert s.loc[9, "months"] == 28 and s.loc[9, "silent"] and not s.loc[9, "listed"]  # > 24 months
    assert s.loc[10, "silent"] and not s.loc[10, "listed"]  # only 5 months of data


def test_national_median_needs_five_markets():
    assert national_medians(panel({i: full() for i in range(1, 5)}), AUG).empty
    med = national_medians(panel({i: full(100.0 + i) for i in range(1, 6)}), AUG)
    assert np.exp(med["median_lp"].iloc[0]) == pytest.approx(103.0) and med["n_markets"].iloc[0] == 5


def test_permanent_gap_is_not_highlighted_but_widening_gap_is():
    others = {i: full() for i in range(1, 7)}
    remote = full(150.0)  # always 50 % above
    blockaded = full(110.0, 44) + [110.0, 130.0, 160.0, 190.0]  # usually 10 % above, now 90 %
    p = panel(others | {7: remote, 8: blockaded})
    g = series_gaps(p, national_medians(p, AUG), AUG).set_index("series_id")
    r, b = g.loc["mali|7|1|Retail|KG"], g.loc["mali|8|1|Retail|KG"]
    assert np.exp(r["gap"]) == pytest.approx(1.5) and np.exp(r["usual_gap"]) == pytest.approx(1.5)
    assert not r["far_above_usual"]
    assert np.exp(b["gap"]) == pytest.approx(1.9) and np.exp(b["usual_gap"]) == pytest.approx(1.1)
    assert b["far_above_usual"] and b["n_markets"] == 8


def test_cheaper_than_usual_is_not_highlighted():
    p = panel({i: full() for i in range(1, 7)} | {7: full(100.0, 44) + [40.0] * 4})
    g = series_gaps(p, national_medians(p, AUG), AUG)
    assert not g["far_above_usual"].any()


def test_known_data_errors_are_not_used():
    p = panel({i: full() for i in range(1, 7)} | {7: full()})
    i = p.index[(p["market_id"] == 7) & (p["m"] == AUG)][0]
    p.loc[i, ["lp", "suspect_from"]] = np.log(1000.0), AUG  # an extra zero, known by August
    g = series_gaps(p, national_medians(p, AUG), AUG).set_index("series_id").loc["mali|7|1|Retail|KG"]
    assert g["month"] == AUG - 1 and np.exp(g["gap"]) == pytest.approx(1.0)


def test_months_after_data_up_to_change_nothing():
    base = panel({i: full() for i in range(1, 8)} | {8: full()[:-3] + [None] * 3})
    later = pd.concat([base, panel({8: [500.0] * 2, 1: [900.0] * 2}, start=AUG + 1)], ignore_index=True)
    a, b = compute_signals(base, AUG), compute_signals(later, AUG)
    assert a.reference == b.reference
    pd.testing.assert_frame_equal(a.markets, b.markets)
    pd.testing.assert_frame_equal(a.gaps, b.gaps)


def test_silent_series_stay_in_the_export():
    p = panel({i: full() for i in range(1, 8)} | {8: full()[:-3] + [None] * 3, 9: full()[:20] + [None] * 28})
    s = compute_signals(p, AUG)
    known = {f"mali|{i}|1|Retail|KG" for i in range(1, 8)}
    extra = silent_series(p, s, known)
    assert extra["series_id"].tolist() == ["mali|8|1|Retail|KG"]  # 3 months silent; market 9 stopped 28 months ago
    assert extra["m_last"].iloc[0] == AUG - 3 and extra["months_reported_12"].iloc[0] == 9


def test_signal_texts_use_only_facts():
    import re
    from fpw.signals import describe_signals, signal_facts
    from fpw.texts import SIGNAL_TEXTS
    gap = {"month": AUG, "gap": np.log(1.92), "usual_gap": np.log(1.08), "n_markets": 24, "far_above_usual": True}
    f = signal_facts(gap, {"silent": False, "months": 0, "last_month": AUG}, AUG, "burkina-faso")
    assert describe_signals(f) == ("In August 2026 the price here was 92% above the national median of 24 markets "
                                   "(usually 8% above). " + SIGNAL_TEXTS["en"]["far"])
    fr = describe_signals(f, "fr")
    assert fr.startswith("En août 2026, le prix ici était 92 % au-dessus de la médiane nationale de 24 marchés "
                         "(d'habitude 8 % au-dessus).")
    quiet = signal_facts(gap, {"silent": True, "months": 3, "last_month": AUG - 3}, AUG, "mali")
    assert quiet["gap"] is None  # a stale gap is not shown for a silent market
    assert describe_signals(quiet).startswith("No price has been published for this market since May 2026, while "
                                              "most markets in Mali reported up to August 2026.")
    near = signal_facts({**gap, "gap": np.log(0.99), "usual_gap": np.log(0.8), "far_above_usual": False}, None, AUG,
                        "mali")
    assert describe_signals(near) == ("In August 2026 the price here was about the same as the national median of 24 "
                                      "markets (usually 20% below).")
    assert describe_signals(signal_facts(None, None, AUG, "mali")) == ""
    for lang in ("en", "fr"):
        for facts in (f, quiet, near):
            nums = set(re.findall(r"\d+", describe_signals(facts, lang)))
            g = facts["gap"] or {}
            allowed = {str(abs(g.get(k))) for k in ("pct", "usual_pct", "n") if g.get(k) is not None} | {"2026"}
            assert nums <= allowed, (lang, nums - allowed)
        assert set(SIGNAL_TEXTS[lang]) == set(SIGNAL_TEXTS["en"])


def test_a_stopped_food_in_an_active_market_is_not_a_silent_market():
    millet = panel({i: full() for i in range(1, 8)})
    rice = panel({1: full()[:-4] + [None] * 4, 2: full(), 3: full(), 4: full(), 5: full()}, commodity_id=2)
    p = pd.concat([millet, rice], ignore_index=True)  # market 1 still reports millet, its rice stopped
    s = compute_signals(p, AUG)
    assert not s.markets["silent"].any()
    assert silent_series(p, s, set(millet["series_id"]) | {f"mali|{i}|2|Retail|KG" for i in (2, 3, 4, 5)}).empty


def test_an_old_gap_is_not_shown():
    from fpw.signals import signal_facts
    old = {"month": AUG - 5, "gap": np.log(5.0), "usual_gap": 0.0, "n_markets": 9, "far_above_usual": True}
    assert signal_facts(old, None, AUG, "mali")["gap"] is None  # e.g. an unconfirmed jump five months ago
    assert signal_facts({**old, "month": AUG - 1}, None, AUG, "mali")["gap"] is not None
