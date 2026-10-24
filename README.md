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

**Where it stands.** *Phase 4 is done:* every Monday the project downloads WFP's latest prices for **Mali,
Burkina Faso and Burundi**, checks them, and makes forecasts for the next months with the method chosen in Phase 3.
The forecasts are stored before anyone knows the outcome, so they can be scored honestly later. A private web page
(only for people with a login to the project's Databricks workspace) shows, per market and food: the price history,
the forecast range, the chance of a spike, a short explanation in words, and the track record. Nothing is public yet.

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

**Preparation for a market food basket, and two data checks** (requested after reviewing
`docs/proposal-users-and-features.md`; analyses only, no model change):
- Forecast rows now carry `market_id`, `series_commodity_id` and `unit` (panel, cases, backtest tables), so forecasts
  can be grouped per market. Every forecast row already stores its PIT and an 11-level quantile grid: what a basket
  built from correlated item forecasts needs. Basket compositions and unit conversions are to be kept as versioned
  data files when that work starts. (The Databricks gold table gets the new columns at the next `fpw_backtest` run.)
- **Do markets go silent after a spike?** Mildly. Share of target months missing (step 3): 11.2 % when z < 0 at the
  origin, 12.7 % in alert, and since 2023 18.7 % in crisis (z >= 2) vs 12.6 %. Series silent for all 5 following
  months: Burundi 3.1 % in alert vs 1.7 % not, Mali 4.3 % vs 3.6 %, Burkina Faso 0.2 % vs 0.3 %. So spike metrics
  are computed on slightly fewer cases in crisis states; the bias is modest, not dramatic.
- **Are blockade-town spikes excluded as suspect?** No. Djibo, Arbinda, Sebba, Gorom Gorom, Dori, Titao, Diapaga and
  Fada N'Gourma report every year to 2026 (with gaps, e.g. Djibo Oct 2025 - Jan 2026); only 2 of their 7,720 retail
  rows were ever flagged `spike_revert` (2015, 2021).
- **Open finding: repeated prices.** Djibo millet is exactly 368 and sorghum exactly 316 XOF/kg from June to
  September 2026, well below 2023-25, while FEWS NET reports blockade price rises in the area. Share of retail
  prices inside a run of >= 4 identical consecutive months: Mali 30 % before 2020, 22 % 2020-22, 16 % since 2023;
  Burkina Faso 6-7 %; Burundi 1-3 %. Real sticky prices or values carried forward without collection cannot be told
  apart from the data; this makes affected series look calmer than they are. Candidate (to decide): a
  `repeated_price` flag that keeps the values but marks them, and a question to WFP.
- **WFP's variability rule applied** (from WFP's forecasting/ALPS method note: show a series only if cv >= 15 %
  over the whole series or >= 10 % over the last 3 years, or (max - min) / mean >= 50 % / 30 %; suspect rows
  excluded; "pv" read as range over the mean price). Of our 909 eligible series only **11 fail** the full rule
  (Burkina Faso 9, Mali 2): over decades of inflation almost every series varies enough. The 3-year part is more
  telling: **85 series are flat in the last 3 years** (both 3-year indicators below threshold): Mali 52, Burkina
  Faso 26, Burundi 7. They are the repeated-price series: median 44 % of their last-3-year months sit in runs of
  >= 4 identical prices, against 0 % for the other series; of series with > 60 % repeated months, 59 % are flat.
  The flattest are **imported rice in Bamako districts** (Niarela, Kouremale, Djikoroni, Lafiabougou: 85-96 %
  repeated months), plausibly a really stable import price. The blockade towns pass (Djibo millet 23 % repeated),
  except Sebba imported rice (63 %).

**Gotchas found**
- Two test failures were sampling noise in my own tests (100-300 PITs give a 90 % quantile SE of 0.017-0.03 in level;
  seed 1 started ~3 SE low); judged over seeds instead of loosening thresholds.
- LightGBM's scikit-learn API needs `scikit-learn`; macOS needs `libomp` (Homebrew).
- `grep` in a pipe buffers a long-running script's log until it ends: use `python -u` or no filter.
- LightGBM is not bit-for-bit reproducible across machines (thread count x row sampling): the Databricks run gave
  lgbm_cal holdout pinball 0.0274 vs 0.0276 locally (validation 0.0258 vs 0.0257); baselines match exactly. The
  conclusions are the same. Backtest job on serverless: 27.7 min (3 baselines + lgbm + recalibration, 2.2 M rows).
- **The 2023+ holdout is now spent twice.** Model changes from here are judged on the live track record.

### Review fixes (external review 2026-10-24, `docs/review-2026-10-24-backtest.md`)

- **Issue 1, look-ahead through the suspect flags (confirmed, fixed).** `spike_revert` is decided with the *next*
  month, but suspect rows were removed before the backtest, so a blip in the last usable month (O - 2) was already
  gone at origin O, while a live run would still see it. Affected: 76 of 122,689 scored series-origin cases (0.06 %).
  My no-look-ahead test missed it because its simulated panels skip `flag_suspects`. Now `flag_suspects` records
  `confirmed_date`, the panel keeps suspect rows with `suspect_from`, and `backtest.history_at` (shared by the
  baselines and the LightGBM features) drops them only from origins at which that month was published. A new test
  recomputes the real flags on changed future data; under the old code the median forecast differed by 1.12 in log.
  Convention: known data errors are not scored as targets, and the live track record follows the same rule (a target
  month is scored once the following month is published).
- **Issue 3, backtest population vs published population (fixed).** Forecast rows carry `eligible_at_origin` (the
  publication rule, >= 60 usable months and >= 75 % complete, applied to the history at that origin); metrics are
  written for `population` = `all` (model choice) and `eligible` (the track record shown with a forecast).
- **Effect** (Databricks run after the fix; baselines identical to the local run, LightGBM within 0.0003): validation
  mean pinball lgbm_cal 0.0259 (was 0.0257), seasonal_rw_cal 0.0275 (0.0274), seasonal_rw 0.0274 (0.0274), lgbm
  0.0287 (0.0283); **lgbm_cal stays the choice**; holdout differences <= 0.0002 pinball, <= 0.4 points coverage.
  The Phase 2 and Phase 3 tables above were computed before the fix and are left as they were.
- **Published track record: holdout 2023+, series eligible at the origin** (194,652 cases per model, 83 %):

  | Model | Pinball | 80 % cover | 95 % cover | Spike Brier | Onset Brier | Onset clim. |
  |---|---|---|---|---|---|---|
  | **lgbm_cal** | 0.0273 | 78 % | 94 % | 0.123 | 0.108 | 0.112 |
  | seasonal_rw_cal | 0.0282 | 81 % | 96 % | 0.123 | 0.106 | 0.112 |
  | lgbm | 0.0262 | 64 % | 85 % | 0.116 | 0.099 | 0.112 |
  | seasonal_rw | 0.0268 | 69 % | 88 % | 0.119 | 0.099 | 0.112 |

- **Issue 2, revisions** are not simulated and cannot be for the past (snapshots start 2026-10-24): to be stated on
  the methods page; after a few months of weekly snapshots, compare first-seen with current values (Phase 5). Asked
  WFP.
- **Issue 4, "spike" partly measures persistent inflation**: decision (user): keep the ALPS-style definition for
  comparability and explain it on the pages; a short-term "sudden rise" indicator is a later candidate, judged on
  the live track record.
- **Issues 5 and 6**: dropout checked (Phase 3, mild); calibration uses only past, published outcomes, as advised.
- **ALPS reference** (checked against the PDF): WFP, *Technical Guidance Note: Calculation and Use of the Alert for
  Price Spikes (ALPS) Indicator*, April 2014, https://documents.wfp.org/stellent/groups/public/documents/manual_guide_proced/wfp264186.pdf
  (non-commercial reproduction allowed with acknowledgement; we link instead of keeping a copy).

  | | WFP ALPS | food-price-watch |
  |---|---|---|
  | Model | OLS of the price level on a linear trend + 12 monthly dummies, no constant | the same on the log price (relative deviations) |
  | Window | whole series up to now, refit monthly | last 10 years, only data published by the origin |
  | Indicator | residual / sd of residuals (Stata `egen sd`, n - 1) | residual / sigma with n - 13: our z is ~5 % smaller at 120 months |
  | Sign | only positive deviations count (below trend = normal) | signed z; spike = z >= 1, so the same for spikes |
  | Thresholds | normal < 0.25 <= stress < 1 <= alert < 2 <= crisis | spike = z >= 1 (alert or crisis) |
  | Minimum data | 36 months | 36 observations and every calendar month at least twice |
  | Stationarity, breaks | ADF test first; a break dummy advised for single markets | none; `level_shift` flags breaks but the fit does not use them |

  WFP notes that historical ALPS values use the whole series, i.e. information not available at the time (§3.2.4);
  our historical spikes are computed as of each origin, so they will not match WFP's charts. WFP also advises not to
  update the trend during a suspected crisis and to adjust it after devaluations (§3.2.3), which is the same weakness
  as review issue 4. Candidate for later (judged on the live track record): a break dummy when a `level_shift` is
  detected. The note names adjusting cash/voucher transfer values as a use (§2), which supports the basket idea.

### Phase 4: live forecasts and the private app

**Pipeline.** `fpw_training` (first Monday of the month, 06:00) trains the pooled LightGBM quantile model on the
cases published by then and registers it as `workspace.fpw_dev_ml.lgbm_quantile` (MLflow pyfunc wrapping the 11
quantile models, with the `fpw` package as code). Every version gets `@challenger`; it becomes `@champion` only if a
sanity gate passes (finite, non-crossing quantiles, in-sample 80 % coverage 0.6-0.95, enough rows). The gate checks
that a model is not broken; its quality is judged by the backtest and the live track record. The weekly
`fpw_pipeline` gained two tasks:
- `06_live_forecast`: loads `@champion`, forecasts this month's origin with data up to origin - 2 (the backtest
  rule), recalibrates with past published PITs (backtest + scored live), **appends** raw and calibrated rows to
  `gold.live_forecasts` (never overwritten) and rebuilds `gold.live_summary` (one row per series, with the text).
- `07_score_live`: the official forecast per origin is the last run of that month; it is scored once the target
  month and the month after it are published (known data errors are not scored), into `gold.live_scores` and
  `gold.live_metrics`.

**Explanations in words** (`fpw/explain.py`, `fpw/texts.py`): built by code from the model inputs and the forecast
(level vs the usual level for the season, change over 3 months, the same food across the country's markets, the
next-month and 3-month ranges, the spike chance, a fixed caveat). A test checks that every number in the text comes
from the computed facts. Templates are a string catalog, so French is a translation, not a rewrite.

**App** (`app/`, Streamlit as a Databricks App `fpw-dev-<user>`, SQL warehouse, service principal with SELECT on the
gold and silver schemas via `scripts/grant_app_access.sh`): pages *Market and food* (status with icon + label, data
date, explanation, next-month and 3-month ranges, spike chance for next month only, fan chart, table view, country
track record), *Track record* (backtest for eligible series, live once matured, per horizon a verdict whether
new-spike warnings beat the base rate), *Methods* (plain English, limits, ALPS-style vs ALPS). WFP attribution on
every page.

**Results (dev, 2026-10-24).** Model v1: 483,901 training cases, gate passed (in-sample 80 % coverage 0.802),
`@champion`. First live run: origin October 2026, data up to August 2026, 1,091 series x 5 steps, all calibrated.
Status now: Burkina Faso 291 normal / 6 stress; Burundi 403 / 14; Mali 352 normal, 19 stress, 5 alert, 1 crisis.
Headless `AppTest` of all three pages against the real tables: no exceptions. Live scores: none yet (the first
targets mature about three months after the first forecast).

**Track record as the app shows it** (holdout 2023+, eligible series, lgbm_cal): 80 % range held 80 / 79 / 77 / 76 /
76 % for steps 1-5; typical error 5 / 7 / 10 / 13 / 15 %; new-spike warnings better than the base rate for steps
1-3 (next month: Brier 0.109 vs 0.114, -3.9 %) and **worse** at 2 and 3 months ahead (0.134 vs 0.125, 0.154 vs
0.135). The app therefore shows a spike chance for next month only.

**Gotchas found**
- A bundle resource key must be unique, and `data_month` existed twice in the summary schema (series vs run): the
  schema tests caught it (`last_obs_month` for the series).
- `print` output of serverless notebook tasks is not reliably captured: results are read from MLflow tags / tables.
- The plotly default template fights the app theme: transparent background, faint grid.
- The app's own service principal is only exercised when a page is opened in a browser (login needed); checked
  by the user on 2026-10-24: the app works.

**Start / stop the app** (Free Edition: max 3 apps, stopped after 24 h; a running app uses the daily quota):

```bash
databricks bundle run fpw_app -t dev --profile Fx-Workspace       # deploy changes + start
databricks apps stop fpw-dev-sander-grout --profile Fx-Workspace   # stop when done
databricks bundle run fpw_training -t dev --profile Fx-Workspace  # retrain now (also first Monday monthly)
```

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
