from datetime import date

import pandas as pd
import pytest

from fpw.quality import DataQualityError, check_continuations, check_freshness, check_prices, flag_suspects
from helpers import months, prices


def flags(values, start="2017-01"):
    df = flag_suspects(prices(months(start, values)))
    return df.sort_values("date")["quality_flag"].tolist(), df.sort_values("date")["is_suspect"].tolist()


def test_mali_2017_style_one_month_spike_that_reverts_is_suspect():
    # Kita maize, May-Dec 2017 (real values): 140 -> 500 -> 142.
    f, suspect = flags([140, 140, 140, 500, 142, 142, 142, 150], start="2017-05")
    assert f[3] == "spike_revert" and suspect[3]
    assert sum(suspect) == 1  # the months around it are fine


def test_suspects_carry_the_date_they_become_known():
    df = flag_suspects(prices(months("2017-05", [140, 140, 140, 500, 142, 142])
                              + [("2017-11", float("nan"))])).sort_values("date")
    known = dict(zip(df["date"].astype(str), df["confirmed_date"]))
    assert str(known["2017-08-15"]) == "2017-09-15"  # spike_revert: known once the reversal month is out
    assert str(known["2017-11-15"]) == "2017-11-15"  # invalid price: known at once
    assert known["2017-07-15"] is None


def test_milder_market_in_the_same_episode_is_also_caught():
    f, _ = flags([175, 175, 175, 386, 198, 193])
    assert f[3] == "spike_revert"


def test_sustained_rise_is_not_flagged():
    # Lean-season style: doubles over three months and stays high.
    f, suspect = flags([100, 130, 170, 200, 210, 205])
    assert f == [None] * 6 and not any(suspect)


def test_sudden_jump_that_stays_is_a_break_not_a_suspect():
    # Redenomination or unit change: x1000 and the series continues at the new level.
    f, suspect = flags([100, 102, 101000, 102000, 103000])
    assert f[2] == "level_shift" and not any(suspect)


def test_extra_zero_for_one_month_is_spike_revert_and_the_way_back_is_not_a_break():
    # Real case shape: Mali wheat flour 2020, 500 -> 2800 -> 500.
    f, _ = flags([100, 101, 1010, 102, 103])
    assert f == [None, None, "spike_revert", None, None]


def test_jump_that_reverses_partly_next_month_is_not_a_break():
    f, _ = flags([100, 100, 800, 300, 300])
    assert f[2] != "level_shift"


def test_big_jump_in_latest_month_is_kept_as_unconfirmed():
    # Could be a real spike: we cannot know until next month, so it is shown, not excluded.
    f, suspect = flags([100, 101, 102, 190])
    assert f[-1] == "unconfirmed_jump" and not suspect[-1]


def test_no_comparison_across_a_long_gap():
    df = flag_suspects(prices([("2017-01", 100), ("2017-06", 300), ("2017-12", 100)]))
    assert df["quality_flag"].isna().all()


def test_invalid_prices_are_suspect_and_neighbours_compare_around_them():
    df = flag_suspects(prices(months("2017-01", [100, float("nan"), 0.0, 101])))
    assert df["quality_flag"].tolist() == [None, "invalid_price", "invalid_price", None]
    assert df["is_suspect"].tolist() == [False, True, True, False]


def test_series_are_compared_separately():
    df = flag_suspects(prices([
        {"month": "2017-01", "price": 100}, {"month": "2017-02", "price": 100},
        {"month": "2017-01", "price": 500, "market_id": 2}, {"month": "2017-02", "price": 500, "market_id": 2},
    ]))
    assert df["quality_flag"].isna().all()


CURRENCIES = {"mali": ("XOF",)}


def test_check_prices_passes_clean_data():
    check_prices(prices(months("2024-01", [1, 2])), CURRENCIES)


@pytest.mark.parametrize("make, match", [
    (lambda: prices([]).reindex(columns=prices(months("2024-01", [1])).columns), "empty"),
    (lambda: prices([("2024-01", 1.0), ("2024-01", 2.0)]), "duplicate"),
    (lambda: prices(months("2024-01", [1]), currency="USD"), "unexpected currency"),
    (lambda: prices(months("2024-01", [1])), "no prices for"),
])
def test_check_prices_raises(make, match):
    currencies = {**CURRENCIES, "burundi": ("BIF",)} if match == "no prices for" else CURRENCIES
    with pytest.raises(DataQualityError, match=match):
        check_prices(make(), currencies)


def log(*rows):
    return pd.DataFrame(rows, columns=["country", "status", "_ingested_at"])


def test_freshness_ok():
    check_freshness(log(("mali", "unchanged", pd.Timestamp("2026-10-20"))), {"mali": date(2026, 8, 15)},
                    ["mali"], today=date(2026, 10, 24))


def test_freshness_fails_on_failed_fetches_and_old_data():
    fetches = log(("mali", "new", pd.Timestamp("2026-09-01")), ("mali", "invalid", pd.Timestamp("2026-10-20")))
    with pytest.raises(DataQualityError) as e:
        check_freshness(fetches, {"mali": date(2026, 5, 15)}, ["mali", "burundi"], today=date(2026, 10, 24))
    msg = str(e.value)
    assert "mali: no successful fetch" in msg and "mali: latest data month" in msg and "burundi" in msg


def renamed(new_level):
    return prices([
        *[{"month": m, "price": p, "commodity": "Beans", "commodity_id": 50} for m, p in months("2025-09", [100] * 3)],
        *[{"month": m, "price": p, "commodity": "Beans (yellow)", "commodity_id": 829}
          for m, p in months("2025-12", [new_level] * 3)],
    ], country="burundi", currency="BIF")


def test_check_continuations_accepts_same_price_level():
    check_continuations(renamed(97.5), {("burundi", 50): 829})


def test_check_continuations_rejects_a_level_jump():
    # e.g. the new commodity is quoted per 50 KG bag, or the link is simply wrong
    with pytest.raises(DataQualityError, match=r"burundi 50->829: median price changes \+400%"):
        check_continuations(renamed(500.0), {("burundi", 50): 829})


def test_a_record_only_country_with_old_data_does_not_stop_the_run_but_a_failed_fetch_does():
    fetches = log(("mali", "unchanged", pd.Timestamp("2026-10-20")), ("chad", "new", pd.Timestamp("2026-10-20")))
    latest = {"mali": date(2026, 8, 15), "chad": date(2026, 6, 15)}  # Chad: published months late
    check_freshness(fetches, latest, ["mali", "chad"], today=date(2026, 10, 27), data_age_countries=["mali"])
    with pytest.raises(DataQualityError, match="chad: no successful fetch"):
        check_freshness(log(("mali", "unchanged", pd.Timestamp("2026-10-20"))), latest, ["mali", "chad"],
                        today=date(2026, 10, 27), data_age_countries=["mali"])
