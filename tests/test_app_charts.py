from datetime import date

import numpy as np
import pandas as pd

from charts import fan_chart, month_date
from fpw.panel import month_date as fpw_month_date
from strings import STATUS, month_label, skill_verdict


def history():
    d = pd.date_range("2024-03-01", periods=30, freq="MS") + pd.Timedelta(days=14)  # ends August 2026
    suspect = [False] * 30
    suspect[20] = True
    return pd.DataFrame({"date": d.date, "price": 300 + 10 * np.sin(np.arange(30)), "is_suspect": suspect})


def forecast():
    m = 2026 * 12 + 7
    lp = np.log(310.0)
    return pd.DataFrame({"target": [m + s for s in range(1, 6)], "q025": lp - 0.3, "q10": lp - 0.15, "q50": lp,
                         "q90": lp + 0.15, "q975": lp + 0.3, "expected": lp - 0.05})


def test_month_helper_mirrors_the_pipeline():
    for m in [2003 * 12, 2026 * 12 + 9, 2027 * 12 + 11]:
        assert month_date(m) == fpw_month_date(m)
    assert month_label(2026 * 12 + 9) == "October 2026"


def test_fan_chart_traces_and_values():
    fig = fan_chart(history(), forecast(), "XOF", "KG")
    names = [t.name for t in fig.data]
    assert names == ["Price (observed)", "Data error (not used)", "95 % range", "80 % range",
                     "Forecast (most likely)", "Usual level for the season"]
    median = fig.data[4]
    last_price = history()["price"].iloc[-1]
    assert median.x[0] == date(2026, 8, 15) and np.isclose(median.y[0], last_price)  # starts at the last observation
    assert np.allclose(median.y[1:], 310.0) and median.x[1] == date(2026, 9, 15)
    band80 = fig.data[3]
    assert np.isclose(max(band80.y), 310 * np.exp(0.15)) and np.isclose(min(band80.y), 310 * np.exp(-0.15))
    assert len(fig.data[0].x) == 29  # the data error is drawn separately, not on the price line
    assert fig.layout.hovermode == "x unified" and fig.layout.yaxis.title.text == "XOF per KG"


def test_fan_chart_without_forecast_shows_history_only():
    fig = fan_chart(history().assign(is_suspect=False), None, "XOF", "KG")
    assert [t.name for t in fig.data] == ["Price (observed)"]


def test_status_has_icon_and_label():
    assert set(STATUS) == {"normal", "stress", "alert", "crisis"}
    assert all(icon and label for icon, label, _ in STATUS.values())


def test_skill_verdict_matches_the_holdout_numbers():
    assert skill_verdict(0.0985, 0.112) == "better than the base rate"
    assert skill_verdict(0.1093, 0.1137) == "better than the base rate"  # next month, lgbm_cal: -3.9 %
    assert skill_verdict(0.1100, 0.1120) == "no better than the base rate"
    assert skill_verdict(0.1544, 0.1347) == "worse than the base rate"  # in 3 months
