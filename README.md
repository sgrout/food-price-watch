# food-price-watch

## In plain English

**What it does.** When the price of a basic food like maize, millet or rice jumps in a local market, families
who already spend most of their income on food are hit first. The World Food Programme (WFP) collects these prices
every month in thousands of markets and shares them openly. This project reads those prices and estimates, per market
and per food, where the price is likely to be in one to three months, and how likely a sharp, unusual rise (a "spike")
is.

**How sure it is.** It never gives a single number as if it were certain. Every forecast is a range ("most likely
between X and Y"), and the project keeps an honest record of how often past forecasts were right, which is published
next to every forecast.

**What it is not.** It does not replace WFP or FEWS NET, who make the official food-security assessments. It is a free,
open extra tool for small organizations without their own data team. It earns no money.

**Where it stands.** *Phase 1 (data) is done.* Every Monday the project downloads WFP's latest prices for the three
pilot countries, **Mali, Burkina Faso and Burundi**, keeps every version it has seen, and checks the data. About
320,000 prices go back to 2003. There are no forecasts yet; that is Phase 2.

**What the checks found.** Food price data has mistakes, and we mark them rather than quietly correcting them:
- In August 2017, the maize price in most Malian markets tripled for exactly one month and then went back to normal.
  A real price spike does not vanish that fast, so these values are marked "suspect" and will not be used to train
  forecasts (743 of 320,000 prices, about 1 in 430, are marked this way).
- In December 2025 WFP renamed "Beans" in Burundi to "Beans (yellow)". We link the two so the 20-year bean history is
  not lost, and the computer checks that the price level really stays the same at the switch.
- The newest month is always incomplete for a while: prices appear on the website one to two and a half months
  after the month they describe. Forecasts will only use what was actually available at the time.

**How much is usable.** A food in a market needs at least 5 years of mostly complete, recent prices before we will
forecast it. That gives **909 series**: Mali 244, Burkina Faso 291, Burundi 374 (maize, millet, sorghum, rice, beans,
cassava flour, cooking oil).

**How good are simple forecasts? (Phase 2).** Before trying anything clever we tested three simple methods on the
past: we pretended to stand in every month since 2008, used only what had been published by then, made a forecast,
and compared it with what really happened. The best simple method ("same seasonal pattern as in earlier years")
was chosen on 2020-2022 and then checked once on 2023-2026:
- Its typical error is about 9 % of the price for next month and about 12 % for three months ahead.
- Its "80 % range" contained the real price only **about 7 times in 10**. The ranges are too narrow; that must be
  fixed before anyone sees them (first task of Phase 3).
- Spikes (a price clearly above what is normal for that time of year) were common: about 1 in 8 months before 2020,
  1 in 2 in 2020-2022 (the world food price crisis and conflict in the Sahel), almost 1 in 3 since 2023.
- Once a market is in a spike it usually stays there for months, so "it is high now" is already a strong signal.
  The hard part is a *new* spike: when the method said a new spike was more likely than not for next month, it was
  right about **half the time (47 %)** and caught **about 1 in 5 (21 %)** of the new spikes. Better than
  guessing, far from perfect, and that is what we will say on every page.

**A smarter model, and honest ranges (Phase 3).** We then tried a machine-learning model that learns from all
markets at once, and a correction that widens or narrows each forecast range using the method's own past mistakes
(only mistakes that were already known at the time). We fixed the choices in advance, picked on 2020-2022, and
checked once on 2023-2026:
- The correction works for the ranges: the "80 % range" now contains the real price about **3 times in 4 (77 %)**
  instead of 2 in 3. That is the forecast we will show (the machine-learning model, corrected).
- It has a price: the typical error is about 10 % for next month and 15 % three months ahead, a bit more than the
  uncorrected forecasts, because the correction still "remembered" the 2020-2022 crisis when prices calmed down.
- For the same reason its spike warnings were too eager after 2023: when it said "55 % chance", a spike followed
  about 35 % of the time. For new spikes it was **hardly better than just knowing how often spikes happen**. We will
  say so on every page, and keep score from now on with forecasts stored before the prices are known.

**Glossary.**
- *Market / commodity / series:* one food in one market, priced every month, is one "series".
- *Spike:* a price well above what is normal *for that time of year* (prices rise every lean season; that alone is not
  a spike).
- *Bronze / silver / gold:* raw downloads → cleaned data → forecasts and warnings.

Data: World Food Programme, via the Humanitarian Data Exchange (HDX), license CC BY-IGO.

---

## Technical documentation

### Platform

- **Databricks Free Edition** (workspace shared with fx_medallion), CLI profile `Fx-Workspace`, serverless only.
- Catalog `workspace`, schemas `fpw_{env}_bronze|silver|gold|ml`; only the `dev` target is deployed.
- Logic in the package `src/fpw/` (pure functions, unit-tested); notebooks `src/NN_*.py` do parameters and I/O;
  jobs in `resources/*.job.yml`. Later: a private Streamlit app (Databricks App, Databricks login required).

### Phase 0: foundation

- `fpw.InvalidPayload` and `fpw.hdx`: CKAN `package_show` parsing, choosing the price CSV among a dataset's resources,
  and a format check for the CSV (exact header, at least one data row, no HTML).
- Probe job `fpw_probe` (manual, writes nothing), run on serverless on 2026-10-24:

  | country | license | rows | size | latest month |
  |---|---|---|---|---|
  | Mali | CC BY-IGO | 132,286 | 15.6 MB | 2026-08 |
  | Burkina Faso | CC BY-IGO | 59,316 | 7.2 MB | 2026-09 |
  | Burundi | CC BY-IGO | 129,003 | 16.0 MB | 2026-09 |

**Gotchas found**
- The CSV download URL answers with an HTML redirect page to a pre-signed S3 URL. `requests` follows it; a client that
  does not would store an HTML page as "data". The S3 URL carries temporary AWS credentials in its query string, so
  `fetch()` strips the query before the URL is stored (and the test fixture is redacted).
- `priceflag` is `actual`, `aggregate` (a monthly value aggregated from weekly collections) or `actual,aggregate`;
  in some countries `aggregate` carries most rows since ~2016. Keep it, with the flag, rather than dropping it.
- **Point in time:** the CSV has no publication date per row, and HDX replaces the file instead of keeping versions.
  From the first ingestion on, bronze snapshots (with `_ingested_at`) record what was known when; for older history,
  backtests have to assume a publication lag (to be estimated in Phase 1 from successive snapshots).
- Local PySpark 4 does not support pandas 3 yet, so `pandas<3` is pinned (Databricks serverless ships pandas 2.x).

### Phase 1: ingest the pilot countries

Job `fpw_pipeline` (weekly, Monday 07:00 Amsterdam, serverless, email on failure):

| Task | Writes | What |
|---|---|---|
| `01_bronze_hdx` | volume `fpw_dev_bronze.raw`, table `hdx_fetch_log` | HDX metadata check; download only if the resource timestamp changed; file stored as received (also invalid payloads, as `.invalid`); every attempt logged as `new` / `unchanged` / `invalid` / `error` |
| `02_silver_prices` | `fpw_dev_silver.wfp_price_versions`, `wfp_prices`, `exchange_rates` | Versions: a row only for new, changed (price/priceflag) or removed keys, `valid_from` = snapshot time, so `fpw.silver.as_of(t)` gives the data as known at t. Current tables rebuilt from versions after the hard checks pass |
| `03_gold_coverage` | `fpw_dev_gold.series_coverage`, `country_coverage` | History, completeness, recency, flags and eligibility (or the reason not) per series; then the freshness check |

**Results (dev, 2026-10-24).** First run 180 s; 320,605 versions; 320,433 food prices and 172 exchange-rate rows.
Second run: three `unchanged` checks, no downloads, identical row counts and table hash (idempotent).

| Country | Markets | Series | Retail staple series | Eligible | Eligible markets | Median years | Suspect rows | Latest month |
|---|---|---|---|---|---|---|---|---|
| Burkina Faso | 66 | 444 | 322 | 291 | 62 | 11.7 | 15 | 2026-09 |
| Burundi | 72 | 1,537 | 700 | 374 | 65 | 8.3 | 321 | 2026-09 (partial) |
| Mali | 137 | 3,778 | 1,325 | 244 | 70 | 17.3 | 407 | 2026-08 |

Eligible = retail staple, >= 60 usable months, >= 75 % of months present, data within 3 months of the country's
latest month (starting rules, to revisit with the Phase 2 backtest).

**Quality flags** (`fpw/quality.py`; values are never changed):
- `spike_revert` (suspect, excluded by default): > x1.75 in one month and back within x1.3 the next month. Mali maize
  Aug 2017: 46 of 68 markets flagged; the other 22 had a milder jump, a missing neighbour month, or did not fully
  revert (e.g. 156 -> 500 -> 209). A rule on single series cannot catch all of such a country-wide episode; a
  cross-market rule is a candidate if the backtest shows it matters.
- `level_shift` (break, kept): > x5 that persists. 65 in Mali, 17 in Burundi, mostly livestock, eggs and fish. A
  first version also flagged the month *after* a spike_revert (the way back); fixed and tested.
- `unconfirmed_jump` (kept): > x1.75 in a series' latest month; may be a real spike, judged next month.
- `invalid_price`: missing or <= 0 (none in the pilots).

**Hard checks** (stop the run before silver is overwritten): empty, duplicate keys, unexpected currency per country,
a country without data, a commodity link whose price level changes > 25 % at the switch; freshness (no successful
fetch for 14 days, or latest data month older than 120 days).

**Gotchas found**
- Commodities get re-specified under a new id: Burundi "Beans" (50) ends 2025-11 and "Beans (haricot, yellow)" (829)
  starts 2025-12 in 70 of the same 72 markets at the same level (-2.5 %). Linked in `fpw.countries.CONTINUATIONS`
  (`series_commodity_id`); the original ids are kept. Without the link Burundi had no eligible bean series. WFP also
  stopped local rice and fish in Burundi after 2025-11 (no successor).
- WFP price files contain exchange rates as a "commodity" (Burundi `Exchange rate (unofficial)`, unit `USD/LCU`,
  2010-01 to 2024-04): split into `exchange_rates`, a driver candidate for Phase 3.
- Mali has 97 market/commodity combinations quoted in more than one unit, so the unit is part of the series key.
- **Publication lag.** HDX updates the files weekly (Sundays ~09:30 UTC). The CKAN activity stream
  (`package_activity_list`, last ~100 changes) shows when each data month first appeared: 1 to 2.5 months after the
  15th (e.g. Burkina Faso 2026-09 on 10-18, Mali 2026-08 on 10-18). A month is incomplete when it first appears
  (Burundi 2026-09: 109 of ~1,020 rows), which the weekly snapshots measure from now on.
- Writing pandas to Delta: explicit DDLs (`fpw/schemas.py`) because an all-null column cannot be inferred and NaN
  must become NULL; a test checks every frame against its schema.

### Phase 2: baselines and walk-forward backtest

**Setup** (`fpw/panel.py`, `spike.py`, `baselines.py`, `backtest.py`; job `fpw_backtest`, manual, MLflow experiment
`fpw_backtest_dev`).
- Panel: retail staples from `silver.wfp_prices`, suspect rows excluded, one log price per series and month.
- Point in time: at origin month O only data up to O - 2 is used (publication lag, see Phase 1). Steps 1-5 are
  counted from that month: 1-2 = nowcast, 3-5 = the next 1-3 calendar months. A series needs >= 36 observations and
  data within 2 months of O - 2. Every model is refit at every origin (2008-01 onwards).
- Spike (ALPS-style): z = (log price - expected) / sigma from a seasonal-level + linear-trend fit on the last 10
  years of usable data; spike = z >= 1. *Onset* = a spike at the target for a series not in alert at the origin.
- Candidates (fixed up front): `naive` (random walk; sqrt(k)-scaled empirical 1-month changes), `seasonal_rw` (last
  value + mean k-month change for the calendar month + empirical residuals), `alps_ar1` (seasonal trend + AR(1)
  residual, Gaussian, with parameter variance). Spike probability = each model's predictive P(above threshold).
- Splits by target month: dev < 2020, validation 2020-2022 (choose: lowest mean pinball over steps 1-5, in code
  `choose_model`), holdout 2023+ (checked once). Same cases for every model (`common_rows`): 573,448 per model,
  1,417 series.

**Results** (means over steps 1-5; "onset clim." = Brier score of always forecasting the onset base rate):

| Split | Model | Pinball | 80 % cover | 95 % cover | Spike Brier | Onset Brier | Onset clim. |
|---|---|---|---|---|---|---|---|
| validation | **seasonal_rw** | **0.0274** | 66 % | 83 % | **0.135** | 0.160 | 0.196 |
| validation | naive | 0.0292 | 69 % | 89 % | 0.142 | 0.159 | 0.196 |
| validation | alps_ar1 | 0.0349 | 65 % | 82 % | 0.199 | 0.185 | 0.196 |
| holdout | **seasonal_rw** | **0.0270** | 69 % | 87 % | **0.123** | **0.103** | 0.117 |
| holdout | naive | 0.0281 | 74 % | 92 % | 0.131 | 0.115 | 0.117 |
| holdout | alps_ar1 | 0.0282 | 78 % | 92 % | 0.136 | 0.104 | 0.117 |

- **Chosen: `seasonal_rw`**, confirmed on the holdout (best pinball, spike and onset Brier).
- **Negative: intervals are too narrow** for every model after 2020 (seasonal_rw 80 % interval: 69 % on the
  holdout, 66 % on validation; dev 74 %); high spike probabilities are overconfident (holdout: forecast 0.85 ->
  observed 0.73). Not publishable as is; calibration is the first task of Phase 3.
- Spike base rate: dev 12 %, validation 50 %, holdout 29 % (step 3). Persistence ("in alert now -> in alert at the
  target") has precision 0.73 / recall 0.65 at step 3 on the holdout, so the onset metrics are the real test.
  Onsets at step 3 = next month (holdout, alert at p >= 0.5): seasonal_rw precision 0.47, recall 0.21; Brier 0.106
  vs 0.120. Median |log error| seasonal_rw holdout: 0.086 at step 3, 0.114 at step 5.
- `alps_ar1` assumes prices return to their old trend; after the 2020-22 shocks they did not, so its spike
  probabilities were far too low on validation (forecast 0.24 -> observed 0.59). It never issues an onset alert.
- In dev, `naive` onset Brier is worse than climatology at steps 3-5: a random walk has no seasonal knowledge.

**Gotchas found**
- On simulated data, before any real result: `naive` with overlapping k-month changes undercovered (72.5 % at step
  5) and `alps_ar1` without parameter uncertainty had too-low spike probabilities; both specs fixed and tested.
- The fitted residual sd is biased low (~10 %) for persistent residuals: a 10-year trend absorbs slow movements.
- The holdout has now been used for these baselines. Phase 3 needs its own clean test (e.g. a later holdout start
  or the live track record) and must not tune on 2023+.
- Bundle resource keys must be unique across types (`fpw_backtest` job and experiment clashed); one resource per
  `<name>.<type>.yml` file.

### Phase 3: recalibration and a pooled ML model

**Candidates, fixed before the backtest:** `seasonal_rw` (Phase 2 winner), `seasonal_rw_cal`, `lgbm`, `lgbm_cal`.
Selection: lowest validation mean pinball (`choose_model(..., candidates=CANDIDATES)`); ML only if it beats the best
baseline; holdout 2023+ once (it had already been used once to confirm the Phase 2 baseline). Same cases for all
models (`common_rows`; ML starts in 2012, so dev = 2012-2019).

- **Recalibration** (`fpw/calibrate.py`): quantile recalibration with past PITs. At origin O, the PITs of forecasts
  whose target was published by O (target <= O - 2), last 60 months, per model x country x step, >= 300; quantile'(tau)
  = quantile(G^-1(tau)) and P'(spike) = 1 - G(1 - P(spike)). Grids are interpolated in normal-score space with
  linear tails (`fpw/distribution.py`), so an interval can widen beyond the model's own 97.5 % quantile.
- **Pooled LightGBM** (`fpw/features.py`, `fpw/ml.py`): 11 quantile models (2.5 % ... 97.5 %) of the log change from
  the last observation; 22 features: step, k, target month, history length, ALPS state (z now, residual, sigma, phi,
  expected seasonal change), momentum (1/3/6/12-month changes, 12-month volatility), the seasonal_rw median change and
  80 % width, the same food's median 1- and 3-month change and z across the country's markets, country and commodity
  group. Refit every January on cases published by then (purge), last 10 years; fixed parameters (250 trees,
  learning rate 0.06, 31 leaves, min 200 rows per leaf, 80 % row and column sampling). Quantiles sorted (no crossing).

**Results** (means over steps 1-5):

| Split | Model | Pinball | 80 % cover | 95 % cover | Spike Brier | Onset Brier | Onset clim. |
|---|---|---|---|---|---|---|---|
| validation | **lgbm_cal** | **0.0257** | 75 % | 93 % | **0.126** | **0.143** | 0.196 |
| validation | seasonal_rw_cal | 0.0274 | 75 % | 93 % | 0.131 | 0.154 | 0.196 |
| validation | seasonal_rw | 0.0274 | 66 % | 83 % | 0.135 | 0.160 | 0.196 |
| validation | lgbm | 0.0283 | 60 % | 80 % | 0.139 | 0.159 | 0.196 |
| holdout | lgbm | **0.0262** | 65 % | 85 % | **0.119** | **0.102** | 0.117 |
| holdout | seasonal_rw | 0.0270 | 69 % | 87 % | 0.123 | 0.103 | 0.117 |
| holdout | **lgbm_cal** | 0.0276 | 77 % | 93 % | 0.128 | 0.115 | 0.117 |
| holdout | seasonal_rw_cal | 0.0283 | **80 %** | **96 %** | 0.126 | 0.109 | 0.117 |

- **Chosen (rule, kept after the holdout by decision of the user): `lgbm_cal`.** It beats the calibrated baseline on
  the holdout pinball (0.0276 vs 0.0283) but not on spike Brier (0.128 vs 0.126), and the raw models are sharper.
- **Recalibration fixes coverage** (holdout 80 % interval: 65 -> 77 % for lgbm, 69 -> 80 % for seasonal_rw) but
  **costs sharpness and spike skill after 2023**: the 60-month PIT window still holds the 2020-22 crisis errors, so it
  over-widens and over-predicts spikes when prices calm down (lgbm_cal: forecast 0.55 -> observed 0.35). Onset Brier
  of lgbm_cal 0.115 vs climatology 0.117: **no meaningful skill for new spikes on the holdout**. At step 3 (next
  month) its onset alerts (p >= 0.5) had precision 0.42 and recall 0.51.
- Raw lgbm is the least honest model (validation 80 % interval: 60 %) but the sharpest; it would be the best model
  if its uncertainty were calibrated without the crisis memory. Candidates for later (to be fixed up front and judged
  on the live track record, not on 2023+): a shorter or recency-weighted PIT window, and calibrating spike
  probabilities separately (e.g. isotonic on past onsets).
- Median |log error| on the holdout, lgbm_cal: 0.095 next month (step 3), 0.144 three months ahead (step 5).

**Gotchas found**
- Two test failures were sampling noise in my own tests (100-300 PITs give a 90 % quantile SE of 0.017-0.03 in level;
  seed 1 started ~3 SE low); judged over seeds instead of loosening thresholds.
- LightGBM's scikit-learn API needs `scikit-learn`; macOS needs `libomp` (Homebrew).
- `grep` in a pipe buffers a long-running script's log until it ends: use `python -u` or no filter.
- LightGBM is not bit-for-bit reproducible across machines (thread count x row sampling): the Databricks run gave
  lgbm_cal holdout pinball 0.0274 vs 0.0276 locally (validation 0.0258 vs 0.0257); baselines match exactly. The
  conclusions are the same. Backtest job on serverless: 27.7 min (3 baselines + lgbm + recalibration, 2.2 M rows).
- **The 2023+ holdout is now spent twice.** Model changes from here are judged on the live track record.

### How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"   # Java 17 needed for PySpark
.venv/bin/pytest

databricks bundle validate --strict -t dev --profile Fx-Workspace
databricks bundle deploy -t dev --profile Fx-Workspace
databricks bundle run fpw_pipeline -t dev --profile Fx-Workspace          # weekly on its own; this runs it now
databricks bundle run fpw_pipeline -t dev --profile Fx-Workspace --only gold_coverage   # one task
databricks bundle run fpw_backtest -t dev --profile Fx-Workspace          # ~28 min on serverless: run only after model changes
```

Rebuild silver from bronze (all files are kept in the volume): drop `fpw_dev_silver.wfp_price_versions` and run the
pipeline; every `new` snapshot in the fetch log is applied again in order.

Clean-up: `databricks bundle destroy -t dev --profile Fx-Workspace` removes the jobs; the schemas `fpw_dev_*` (and the
volume with the raw files) need `DROP SCHEMA ... CASCADE`.
