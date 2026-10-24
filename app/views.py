"""The three pages. Numbers shown come from the gold tables; this file only lays them out."""

import numpy as np
import streamlit as st

import backend
from charts import fan_chart
from strings import NOT_ELIGIBLE, STATUS, month_label, skill_verdict

NEXT_STEP, LAST_STEP = 3, 5  # next month, three months ahead (see fpw.backtest)


def _status_badge(status: str) -> str:
    icon, label, colour = STATUS[status]
    return f"<span style='color:{colour}; font-weight:600'>{icon}</span> **{label}**"


def market_page():
    st.title("Market and food")
    series = backend.series_list()
    if series.empty:
        st.info("No live forecasts yet: the weekly pipeline has not produced any.")
        return
    c1, c2, c3 = st.columns(3)
    countries = sorted(series["country"].unique())
    country = c1.selectbox("Country", countries, format_func=lambda c: c.replace("-", " ").title())
    s = series[series["country"] == country]
    commodity = c2.selectbox("Food", sorted(s["commodity"].unique()))
    s = s[s["commodity"] == commodity]
    s = s.assign(label=s["market"] + np.where(s["eligible_at_origin"], "", " (no forecast: not enough data)"))
    row = s.set_index("label").loc[c3.selectbox("Market", sorted(s["label"]))]

    run, data = month_label(row["origin"]), month_label(row["last_obs_month"])
    st.markdown(f"{_status_badge(row['status'])} · prices up to **{data}** · forecast made in **{run}** "
                f"with the data published by then · unit: {row['currency']} per {row['unit']}",
                unsafe_allow_html=True)

    hist = backend.history(row["country"], row["market_id"], row["series_commodity_id"], row["unit"])
    if not row["eligible_at_origin"]:
        st.warning(NOT_ELIGIBLE)
        st.plotly_chart(fan_chart(hist, None, row["currency"], row["unit"]), use_container_width=True)
        return

    st.write(row["explanation"])
    k1, k2, k3 = st.columns(3)
    k1.metric(f"{month_label(row['next_month'])} (80 % range)",
              f"{row['next_q10']:,.0f} – {row['next_q90']:,.0f}", help="8 in 10 chance, if the track record holds")
    k2.metric(f"{month_label(row['last_month'])} (80 % range)", f"{row['last_q10']:,.0f} – {row['last_q90']:,.0f}")
    k3.metric(f"Chance of a spike, {month_label(row['next_month'])}", f"{100 * row['next_spike']:.0f} %",
              help="A spike = price well above the usual level for the season (ALPS-style z >= 1). "
                   "No proven skill yet for new spikes.")

    fc = backend.forecast(row["series_id"])
    st.plotly_chart(fan_chart(hist, fc, row["currency"], row["unit"]), use_container_width=True)
    with st.expander("Table view"):
        table = fc.assign(month=fc["target"].map(month_label))
        for q in ["q10", "q50", "q90", "q025", "q975", "expected"]:
            table[q] = np.exp(table[q]).round(0)
        st.dataframe(table[["month", "q025", "q10", "q50", "q90", "q975", "expected", "spike_prob"]].rename(columns={
            "q025": "2.5 %", "q10": "10 %", "q50": "most likely", "q90": "90 %", "q975": "97.5 %",
            "expected": "usual level", "spike_prob": "spike chance"}), hide_index=True)
        st.dataframe(hist.tail(24), hide_index=True)

    tr = backend.track_record_country(row["country"])
    if len(tr):
        nxt = tr.set_index("step").loc[NEXT_STEP]
        st.caption(f"Track record for {row['country'].replace('-', ' ').title()}, 2023-2026 (forecasts as they could "
                   f"have been made then): the 80 % range contained the real price {100 * nxt['coverage80']:.0f} % of "
                   f"the time for next month; typical error {100 * (np.exp(nxt['median_abs_err']) - 1):.0f} %.")


def track_record_page():
    st.title("Track record")
    st.write("How often past forecasts were right, for the kind of series we publish. Backtest = forecasts made as "
             "they could have been at the time (only data published by then); live = forecasts stored before the "
             "outcome was known.")
    live = backend.live_metrics()
    if live.empty:
        st.info("No live forecast has matured yet. The first are scored about three months after the first live "
                "forecast (October 2026), once the target month and the month after it are published.")
    tr = backend.track_record()
    show = tr[tr["model"].isin(["lgbm_cal", "seasonal_rw_cal", "seasonal_rw"])].copy()
    show["horizon"] = show["step"].map({1: "nowcast: last month", 2: "nowcast: this month", 3: "next month",
                                        4: "in 2 months", 5: "in 3 months"})
    for col in ["coverage80", "coverage95"]:
        show[col] = (100 * show[col]).round(0)
    show["typical error %"] = (100 * (np.exp(show["median_abs_err"]) - 1)).round(0)
    holdout = show[(show["split"] == "holdout") & (show["model"] == "lgbm_cal")].sort_values("step")
    holdout = holdout.assign(verdict=[skill_verdict(a, b) for a, b in
                                      zip(holdout["onset_brier"], holdout["onset_brier_climatology"])])
    st.subheader("Our forecast (lgbm_cal), 2023-2026")
    st.dataframe(holdout[["horizon", "n", "coverage80", "coverage95", "typical error %", "onset_brier",
                          "onset_brier_climatology", "verdict"]].rename(columns={
        "coverage80": "80 % range held (%)", "coverage95": "95 % range held (%)",
        "onset_brier": "new-spike score (lower = better)", "onset_brier_climatology": "same score, base rate only",
        "verdict": "new-spike warnings"}),
        hide_index=True)
    st.caption("'Base rate' = always forecasting how often new spikes happened. Where warnings are no better or "
               "worse than that, they should not be used; the app shows a spike chance for next month only.")
    with st.expander("All models compared, 2020-2022 and 2023-2026"):
        st.dataframe(show[["model", "split", "horizon", "coverage80", "coverage95", "typical error %", "pinball",
                           "brier", "onset_brier"]].sort_values(["split", "model", "horizon"]), hide_index=True)


def methods_page():
    st.title("Methods")
    st.markdown("""
**What this is.** Forecasts of staple food prices per market, 1-3 months ahead, with an honest range and a published
track record. Prices come from the World Food Programme (WFP) via the Humanitarian Data Exchange (HDX). It is a free,
non-commercial tool for organisations without a data team. **It is not** an official assessment: see WFP and FEWS NET.

**How a forecast is made.** One model learns from all markets at once (LightGBM quantile regression) using, for each
food and market: how far the price is from the usual level for that time of year, how it moved over the last months,
and how the same food moves in the country's other markets. It gives a range, not a single number. The range is then
corrected with the model's own past mistakes (only mistakes already known at the time).

**Which data.** A forecast made in a month uses only prices published by then: WFP prices appear 1 to 2.5 months
after the month they describe, so a forecast in October uses prices up to August. Steps 1-2 are therefore
"nowcasts" of months not yet published; steps 3-5 are the next 1-3 months.

**What a spike is.** A price well above the usual level for that time of year: at least one standard deviation above
a seasonal trend fitted on the last 10 years (normal < 0.25 <= stress < 1 <= alert < 2 <= crisis). This is
*ALPS-style*, after WFP's Alert for Price Spikes, with three differences: log prices, a 10-year window, and only
data available at the time (WFP fits the whole series). Historical spikes here will therefore not match WFP's charts.

**Data checks.** Values that jump and fully reverse the next month are marked as data errors and not used (once the
next month is published). Renamed foods are linked when the price level matches. Nothing is silently corrected.

**Known limits.**
- The ranges were too wide and the spike warnings too eager after the 2020-2022 crisis; warnings of *new* spikes have
  no proven skill yet. See the track record.
- Old months may have been revised by WFP; that history cannot be reconstructed, so the backtest uses today's values.
- Some markets report identical prices for many months (e.g. imported rice in Bamako); they may be real or carried
  forward, and make those series look calmer than they are.
- Markets in conflict areas report less often, especially in crises.

**Source and license.** World Food Programme, food prices on HDX, CC BY-IGO.
""")
