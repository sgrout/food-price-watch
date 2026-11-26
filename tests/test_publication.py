from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from fpw import InvalidPayload
from fpw.publication import calendar, forecast_time, month_of, parse_activity_page, published_month, stop_paging

DATA = Path(__file__).parent / "data"


def test_month_of_dataset_date():
    assert month_of("[2003-01-15T00:00:00 TO 2026-08-15T23:59:59]") == 2026 * 12 + 7
    assert month_of(None) is None and month_of("") is None


def test_parse_real_activity_page_keeps_only_non_personal_fields():
    rows = parse_activity_page((DATA / "hdx_activity_mli.json").read_text())
    assert len(rows) == 4 and set(rows[0]) == {"activity_id", "timestamp", "activity_type", "dataset", "dataset_end",
                                               "price_last_modified"}
    assert rows[0]["dataset"] == "wfp-food-prices-for-mali" and month_of(rows[0]["dataset_end"]) == 2026 * 12 + 7
    assert month_of(rows[-1]["dataset_end"]) == 2026 * 12 + 5  # a week earlier the data ended in June


@pytest.mark.parametrize("text", ["<html>Service unavailable</html>", '{"success": false}', '{"success": true, "result": {}}'])
def test_parse_activity_page_rejects_broken_payloads(text):
    with pytest.raises(InvalidPayload):
        parse_activity_page(text)


def test_published_month_is_the_newest_state_at_that_time():
    acts = pd.DataFrame({"country": "mali", "timestamp": ["2026-07-26T10:00:00", "2026-10-11T09:00:00.123456", "2026-10-18T19:48:00"],
                         "dataset_end": ["[2003 TO 2026-05-15T23:59:59]", "[2003 TO 2026-06-15T23:59:59]",
                                         "[2003 TO 2026-08-15T23:59:59]"]})
    cal = calendar(acts)
    assert published_month(cal, "mali", "2026-07-01") is None  # before the calendar starts
    assert published_month(cal, "mali", "2026-10-12") == 2026 * 12 + 5  # June
    assert published_month(cal, "mali", "2026-10-26 06:00") == 2026 * 12 + 7  # August
    assert published_month(cal, "niger", "2026-10-26") is None


def test_forecast_time_is_the_last_monday_of_the_origin_month():
    assert forecast_time(2026 * 12 + 9) == datetime(2026, 10, 26, 6)  # October 2026
    assert forecast_time(2026 * 12 + 10) == datetime(2026, 11, 30, 6)  # November 2026: the 30th is a Monday
    assert forecast_time(2026 * 12 + 11).weekday() == 0 and forecast_time(2026 * 12 + 11).month == 12


def test_data_months_known_fresher_older_or_unknown():
    from fpw.publication import data_months
    acts = pd.DataFrame({"country": "mali", "timestamp": ["2023-01-10T08:00:00", "2026-07-26T10:00:00",
                                                          "2026-10-18T19:48:00"],
                         "dataset_end": ["[2003 TO 2023-06-15T23:59:59]",  # a month that had not ended: projections
                                         "[2003 TO 2026-05-15T23:59:59]", "[2003 TO 2026-09-15T23:59:59]"]})
    dm = data_months(calendar(acts), ["mali"], [2022 * 12 + 11, 2023 * 12, 2026 * 12 + 6, 2026 * 12 + 9])
    assert dm[("mali", 2022 * 12 + 11)] is None  # before the calendar starts
    assert dm[("mali", 2023 * 12)] is None  # January 2023: the dataset claimed June 2023
    assert dm[("mali", 2026 * 12 + 6)] == 2026 * 12 + 4  # July 2026: May published (= origin - 2)
    assert dm[("mali", 2026 * 12 + 9)] == 2026 * 12 + 8  # October 2026: September published (origin - 1)


def test_stop_paging_finishes_an_interrupted_first_fetch():
    page = [{"timestamp": f"2025-0{m}-01T00:00:00"} for m in (9, 8, 7)]
    # end of the stream, or back before the oldest month we need
    assert stop_paging(page[:2], [], 3, "2020-11-01", None)
    assert stop_paging([{"timestamp": "2020-10-01T00:00:00"}] * 3, page, 3, "2020-11-01", None)
    # a full page of new activities: go on
    assert not stop_paging(page, page, 3, "2020-11-01", None)
    # known activities and a complete stored history: caught up, stop
    assert stop_paging(page, page[:1], 3, "2020-11-01", "2020-10-20T00:00:00")
    # known activities but the stored history stops in 2025 (first fetch was interrupted): keep paging
    assert not stop_paging(page, [], 3, "2020-11-01", "2025-07-01T00:00:00")
