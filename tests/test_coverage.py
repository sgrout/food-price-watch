import pandas as pd

from fpw.coverage import MIN_MONTHS, country_coverage, series_coverage
from fpw.quality import flag_suspects
from helpers import months, prices


def frame(*parts):
    return flag_suspects(pd.concat(parts, ignore_index=True))


def long_series(**kw):
    return prices(months("2019-01", [100 + i % 12 for i in range(MIN_MONTHS + 12)]), **kw)  # ends 2024-12


def by_market(cov):
    return cov.set_index("market_id")


def test_long_recent_retail_staple_is_eligible():
    cov = series_coverage(frame(long_series()))
    assert cov["eligible"].all() and cov["reason"].iloc[0] == ""
    assert cov["n_months"].iloc[0] == MIN_MONTHS + 12 and cov["completeness"].iloc[0] == 1.0


def test_reasons_for_ineligible_series():
    cov = by_market(series_coverage(frame(
        long_series(market_id=1),
        long_series(market_id=2, commodity="Livestock (goat)", commodity_id=7),
        long_series(market_id=3, pricetype="Wholesale"),
        prices(months("2023-01", [100] * 24), market_id=4),                         # 2 years only
        prices(months("2019-01", [100] * 36) + months("2022-07", [100] * 30), market_id=5),  # gap: 66/72 ok
        prices(months("2015-01", [100] * 72), market_id=6),                        # stopped in 2020
    )))
    assert cov.loc[2, "reason"] == "not a staple"
    assert cov.loc[3, "reason"] == "not a retail price"
    assert cov.loc[4, "reason"].startswith("less than 60 months")
    assert cov.loc[6, "reason"].startswith("no data in the last")
    assert cov.loc[[1, 5], "eligible"].all()


def test_suspect_rows_do_not_count_as_history():
    values = [100] * MIN_MONTHS
    values[10] = 500  # one spike_revert -> 59 usable months
    cov = series_coverage(frame(prices(months("2020-01", values))))
    assert cov["n_suspect"].iloc[0] == 1 and cov["n_months"].iloc[0] == MIN_MONTHS - 1
    assert not cov["eligible"].iloc[0]


def test_country_summary():
    cov = series_coverage(frame(long_series(market_id=1), long_series(market_id=2),
                                long_series(market_id=2, commodity="Livestock (goat)", commodity_id=7)))
    summary = country_coverage(cov).iloc[0]
    assert summary["markets"] == 2 and summary["series"] == 3
    assert summary["eligible_series"] == 2 and summary["eligible_markets"] == 2
