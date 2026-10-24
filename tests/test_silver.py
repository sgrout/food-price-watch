from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from fpw import InvalidPayload
from fpw.silver import (KEY, as_of, current_from_versions, diff_versions, latest_versions, link_continuations,
                        parse_price_csv, split_exchange_rates)
from helpers import prices

DATA = Path(__file__).parent / "data"
T1, T2, T3 = pd.Timestamp("2026-10-01 06:00"), pd.Timestamp("2026-10-08 06:00"), pd.Timestamp("2026-10-15 06:00")


def empty_versions():
    return pd.DataFrame(columns=KEY + ["price", "priceflag", "is_removed", "valid_from"])


def apply(versions, snapshot, t):
    new = diff_versions(latest_versions(versions), snapshot, t)
    return pd.concat([versions, new], ignore_index=True) if len(versions) else new, new


def test_parse_real_csv_types_and_country():
    df = parse_price_csv((DATA / "wfp_food_prices_mli_head.csv").read_text(), "mali")
    assert len(df) == 20
    assert (df["country"] == "mali").all()
    assert df["date"].iloc[0] == date(2003, 1, 15)
    assert df["price"].dtype == float and df["market_id"].iloc[0] == 247
    assert not df.duplicated(KEY).any()


def test_parse_rejects_unparseable_dates_but_keeps_bad_prices_as_nan():
    text = (DATA / "wfp_food_prices_mli_head.csv").read_text().splitlines()
    good_rows = text[:3]
    bad_price = text[3].rsplit(",", 2)[0] + ",n/a,0.4"
    df = parse_price_csv("\n".join(good_rows + [bad_price]) + "\n", "mali")
    assert df["price"].isna().sum() == 1

    bad_date = "15/01/2003" + text[1][len("2003-01-15"):]
    with pytest.raises(InvalidPayload, match="unparseable"):
        parse_price_csv("\n".join([text[0], bad_date]) + "\n", "mali")


def test_first_snapshot_makes_one_version_per_row():
    snap = prices([("2024-01", 100.0), ("2024-02", 110.0)])
    versions, new = apply(empty_versions(), snap, T1)
    assert len(new) == 2 and not new["is_removed"].any() and (new["valid_from"] == T1).all()


def test_same_snapshot_twice_adds_nothing():
    """Idempotency: rerunning silver on an already-applied snapshot appends no rows."""
    snap = prices([("2024-01", 100.0), ("2024-02", 110.0)])
    versions, _ = apply(empty_versions(), snap, T1)
    _, again = apply(versions, snap, T1)
    assert again.empty


def test_revision_new_month_and_removal_are_versioned():
    v, _ = apply(empty_versions(), prices([("2024-01", 100.0), ("2024-02", 110.0), ("2024-03", 120.0)]), T1)
    # Next snapshot: Jan revised, Feb unchanged, Mar removed at the source, Apr added.
    v, new = apply(v, prices([("2024-01", 105.0), ("2024-02", 110.0), ("2024-04", 130.0)]), T2)
    by_month = {(d.month, removed): p for d, removed, p in new[["date", "is_removed", "price"]].itertuples(index=False)}
    assert set(by_month) == {(1, False), (3, True), (4, False)}
    assert by_month[(1, False)] == 105.0

    cur = current_from_versions(v)
    assert [d.month for d in cur["date"]] == [1, 2, 4]
    jan = cur[cur["date"] == date(2024, 1, 15)].iloc[0]
    assert jan["price"] == 105.0 and jan["first_seen_at"] == T1 and jan["last_changed_at"] == T2
    assert jan["n_versions"] == 2


def test_price_flag_change_is_a_new_version():
    v, _ = apply(empty_versions(), prices([("2024-01", 100.0)], priceflag="aggregate"), T1)
    _, new = apply(v, prices([("2024-01", 100.0)], priceflag="actual"), T2)
    assert len(new) == 1 and new["priceflag"].iloc[0] == "actual"


def test_snapshot_only_compares_its_own_country():
    v, _ = apply(empty_versions(), prices([("2024-01", 100.0)], country="mali"), T1)
    _, new = apply(v, prices([("2024-01", 900.0)], country="burundi", currency="BIF"), T2)
    assert not new["is_removed"].any()  # Mali rows are not tombstoned by a Burundi snapshot


def test_as_of_does_not_see_the_future():
    """No look-ahead: data known at T2 is unchanged by anything ingested later."""
    v, _ = apply(empty_versions(), prices([("2024-01", 100.0)]), T1)
    v, _ = apply(v, prices([("2024-01", 100.0), ("2024-02", 110.0)]), T2)
    before = as_of(v, T2)
    v_future, _ = apply(v, prices([("2024-01", 999.0), ("2024-03", 120.0)]), T3)  # revision + removal + new
    pd.testing.assert_frame_equal(as_of(v_future, T2), before)
    assert len(as_of(v_future, T1)) == 1
    now = as_of(v_future, T3)
    assert sorted(d.month for d in now["date"]) == [1, 3] and now["price"].max() == 999.0


def test_removed_key_that_reappears_is_live_again():
    v, _ = apply(empty_versions(), prices([("2024-01", 100.0)]), T1)
    v, _ = apply(v, prices([("2024-02", 110.0)]), T2)
    v, new = apply(v, prices([("2024-01", 100.0), ("2024-02", 110.0)]), T3)
    assert len(new) == 1
    assert len(current_from_versions(v)) == 2


def test_split_exchange_rates():
    df = prices([
        {"month": "2024-01", "price": 100.0},
        {"month": "2024-01", "price": 2900.0, "commodity": "Exchange rate (unofficial)", "commodity_id": 999,
         "unit": "USD/LCU"},
    ], country="burundi", currency="BIF")
    food, fx = split_exchange_rates(df)
    assert list(food["commodity"]) == ["Maize"] and list(fx["unit"]) == ["USD/LCU"]


def test_link_continuations_keeps_original_ids():
    df = prices([{"month": "2025-11", "price": 1.0, "commodity_id": 50},
                 {"month": "2025-12", "price": 1.0, "commodity_id": 829},
                 {"month": "2025-12", "price": 1.0, "commodity_id": 50, "country": "mali"}], country="burundi")
    out = link_continuations(df.drop(columns="series_commodity_id"), {("burundi", 50): 829})
    assert out["series_commodity_id"].tolist() == [829, 829, 50]  # Mali's id 50 is not linked
    assert out["commodity_id"].tolist() == [50, 829, 50]
