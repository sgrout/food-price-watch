# food-price-watch

Open, free early warning for food price spikes in vulnerable countries: probabilistic forecasts of staple food prices
per local market, honest about uncertainty, published as a public website plus downloadable data for small NGOs and
local organizations that have no data team of their own. Non-commercial; no money-making features.

This file is the brief for coding agents. Read it fully before the first change, and keep it current.

## Project (decided in the first session, 2026-10-24)

- **Platform: Databricks** (chosen by the user as a learning project; overrides the "recommended default" below).
  Workspace `https://dbc-101f908c-607f.cloud.databricks.com` (Free Edition), CLI profile **`Fx-Workspace`**: always
  pass `--profile Fx-Workspace`. The workspace is shared with fx_medallion: same daily quota, same 3-app limit.
- **Catalog / schemas:** catalog `workspace`; schemas `fpw_{env}_bronze|silver|gold|ml` (project prefix keeps them
  apart from fx_medallion's `dev_*`). Deployed target: `dev` only for now.
- **Package:** `fpw` under `src/`; notebooks `src/NN_<layer>_<what>.py`; bundle `databricks.yml` + `resources/`.
- **App:** Streamlit, as a Databricks App, **private to the user** (needs a Databricks login) and started on demand.
  The public static site comes later, after the user decides how to export gold data to a public host.
- **Pilot countries:** Mali, Burkina Faso, Burundi (two data-rich Sahel countries with XOF pegged to the euro, plus a
  high-inflation currency to exercise currency handling).
- **HDX findings from the first probe (laptop, 2026-10-24):** 100 per-country datasets `wfp-food-prices-for-<country>`,
  license CC BY-IGO, columns exactly as listed under Data. The resource download URL answers with an HTML redirect to
  S3 (follow redirects; an unfollowed redirect is an `InvalidPayload`). All dates are the 15th of the month.
  `priceflag` values: `actual`, `aggregate`, `actual,aggregate`; `aggregate` is a monthly value aggregated from
  higher-frequency collections and since ~2016 carries most data in some countries (Nigeria, Malawi, Somalia, South
  Sudan), so keep it and record the flag instead of dropping it. Malawi has a few rows in SOS (data error to flag).
  Coverage (retail staples, >= 96 months, >= 80 % complete, recent): Burkina Faso 261 series / 62 markets, Mali 216 /
  62, Burundi 160 / 58.
- **Serverless probe (2026-10-24, job `fpw_probe`):** HDX API and the S3 redirect are reachable from serverless for
  all three pilots. The CSV has no per-row publication date and HDX overwrites the file, so point-in-time history
  starts with our own bronze snapshots; older backtests need an assumed publication lag (estimate it in Phase 1).
- **Phase 1 conventions (2026-10-24):**
  - Bronze = files as received in volume `fpw_{env}_bronze.raw` + append-only `hdx_fetch_log`; download only when the
    HDX resource `last_modified` changed. HDX updates weekly (Sundays ~09:30 UTC); our job runs Monday 07:00.
  - Silver = `wfp_price_versions` (temporal: a row per new/changed/removed key, `valid_from` = snapshot time) is the
    source of truth for point in time (`fpw.silver.as_of`); `wfp_prices` / `exchange_rates` are rebuilt from it.
  - Series key = `country, market_id, series_commodity_id, pricetype, unit`; renamed commodities are linked only via
    `fpw.countries.CONTINUATIONS`, with evidence in a comment, and are guarded by `check_continuations`.
  - Suspect rows (`is_suspect`) are excluded from history and models by default; never change values.
  - Pandas for logic (the data is small); explicit DDLs in `fpw/schemas.py` + `to_rows` for every table write.
  - Publication lag (CKAN activity stream): a data month first appears 1-2.5 months after the 15th and is then
    incomplete. Phase 2 backtests must assume a lag; "month M usable from M+2" is the conservative default.
- **Phase 2 conventions (2026-10-24):**
  - Backtest: origin O uses data <= O - 2; steps 1-5 from that month (1-2 nowcast, 3-5 = next 1-3 calendar months).
    Splits by target month: dev < 2020, validation 2020-2022, holdout 2023+. Compare models on `common_rows` only.
  - Spike = ALPS-style z >= 1 (`fpw.spike`); report onsets (not in alert at origin) separately from persistence.
  - Selection rule in code (`fpw.backtest.choose_model`: validation mean pinball). Current best baseline:
    `seasonal_rw`. Its intervals are too narrow (holdout 80 % -> 69 %) and must be calibrated before publishing.
  - **The 2023+ holdout is spent** for the baselines; Phase 3 must define a fresh final test and not tune on it.
  - Bundle: one resource per `resources/<name>.<type>.yml`; resource keys unique across types.
- **Phase 3 decisions (2026-10-24):**
  - Production forecast: **`lgbm_cal`** (pooled LightGBM quantile model + PIT recalibration), chosen by the fixed
    rule and kept by the user after a mixed holdout (coverage 77/93 %, pinball 0.0276; spike probabilities
    over-eager after 2023, no onset skill over climatology). Pages must show these holdout numbers and say that new-
    spike warnings have no proven skill yet.
  - The 2023+ holdout is spent. New candidates (shorter/recency-weighted PIT window, separate spike calibration) are
    fixed up front and judged on the live track record only.
  - Backtest notebook `04_backtest.py` runs all models; job `fpw_backtest` uses the `ml` environment (lightgbm).
  - Point in time also for data errors: suspect values are dropped from a backtest history only once their
    `confirmed_date` month is <= origin - 2 (`backtest.history_at`); known errors are never scored, live or backtest.
    Any new test of look-ahead must run the real `flag_suspects`, not only simulated panels.
  - Track record shown with a forecast = metrics with `population = 'eligible'` (eligible at the origin).
  - Spike definition vs WFP ALPS (2014 note, checked): same regression structure and thresholds; ours uses log prices,
    a 10-year origin-only window and sigma with n - 13 (z ~5 % smaller). Comparison table in README; call it
    "ALPS-style", never "ALPS".
- **Phase 4 conventions (2026-10-24):**
  - Production model: UC `workspace.fpw_{env}_ml.lgbm_quantile`, `@champion` via a sanity gate (not a quality gate),
    trained monthly by `fpw_training`; live forecasts use the backtest data rule (origin - 2).
  - `gold.live_forecasts` is append-only (the track record); official forecast = last run of the month; scoring waits
    for the month after the target. Never rewrite or delete live forecasts.
  - User text only from `fpw.explain` facts + `fpw.texts` templates (no hand-written or LLM numbers); a test enforces it.
  - App (`app/`) is self-contained (no `fpw` import); mirrored helpers are tested against `fpw` (`month_date`).
    Spike chance is shown for next month only, because new-spike warnings are worse than the base rate further out.
  - **Public beta (owner's go, 2026-10-25):** the export status is `beta` (job parameter `export_status`); the site
    is public at staplesignals.org with a beta banner. **Exit criterion, fixed before any live result** (owner may
    change it until the first live scores, ~Dec 2026): beta ends when the live 80 % coverage of `lgbm_cal` (eligible
    series) lies between 70 % and 90 % after at least 6 matured forecast months, and the owner agrees.
    Defaults for the launch (owner may change): no search indexing at first (soft launch), French with a
    'translation not reviewed' note, feedback via GitHub Issues.
  - **Food basket (phase 6a, 2026-10-25):** separate jobs `fpw_basket` (weekly) and `fpw_basket_backtest`, tables
    `gold.basket_*` / `live_basket_*`, export `public_export/baskets/` (schema `basket-1.0`); never change the item
    pipeline or export for it. Basket = `config/baskets.csv` (ration-based, not an official MEB; per country what
    WFP monitors). Product `basket_copula`; `basket_comonotone` is a live shadow (holdout tie), decide on live data.
  - **Market signals (phase 6b, 2026-10-27, export 1.4):** distance from the national median and markets that stopped
    reporting (`fpw/signals.py`), descriptions not warnings; silent markets' series stay in the export (history only).
    Deploy 1.4 only after the site accepts it; trial runs with the `export_dir` widget.
  - **Countries (phase 6c, 2026-10-27):** Niger public since 2026-10-29 (owner's go 2026-10-27; the
    `public_countries` bundle variable filters the exports); Chad ingest only (`Country.forecast = False`: WFP
    publishes it 2-4 months late). A new country: probe, `COUNTRIES` + texts + basket, ingest, backtest, train, live,
    review with the owner, then schema/site/`public_countries`.
  - **Fresher data (phase 7, fixed 2026-10-29 before the run):** candidate `lgbm_fresh` starts each case from the
    data month WFP had actually published at the official forecast time (`fpw.publication`, HDX activity stream
    from 2020-12; unknown or earlier: origin - 2), same targets, model and refits; recalibration per (country,
    h = target - data month). Compared with stored `lgbm_cal` on common rows at calendar-known origins, population
    `all` (`13_backtest_fresh.py`, job `fpw_fresh_backtest`). **Switch rule (owner: right after the backtest):**
    replace `lgbm_cal` only if validation mean pinball < `lgbm_cal` with 80 % coverage in [0.70, 0.90], and holdout
    (2023+) mean pinball <= `lgbm_cal` with 80 % coverage in [0.70, 0.90]. Finding: the origin - 2 rule used
    unpublished data in 37 % of Mali's origins (all of 2024), so Mali's current track record is optimistic.
    **Result 1 (2026-10-29): no switch** (validation 0.0234 vs 0.0252 passed; holdout 0.0283 vs 0.0263 failed). The
    loss came from origins where WFP was behind: there `lgbm_cal` used unpublished prices, and `lgbm_fresh` was
    uncalibrated for h >= 6 (too few PITs) and forecast from data up to 15 months old. **Re-test (owner, fixed
    2026-10-29 before the run):** reference `lgbm_cal_pub` = the current model with only published data (data month
    min(published, origin - 2)), calibrated per (country, step) with the published-month PIT cutoff; candidate
    `lgbm_fresh2` = `lgbm_fresh` with calibration per (country, min(h, 5)); both without forecasts when the data
    month is older than origin - 4. Same switch rule, now vs `lgbm_cal_pub`.
    **Result 2 (2026-10-29): switch.** Mean pinball validation 0.0233 vs 0.0256, holdout 0.0251 vs 0.0275 (stored
    `lgbm_cal` 0.0266: optimistic), holdout 80 % coverage 76.4 %; typical error next month 8.2 vs 9.5 %, 3 months
    12.1 vs 14.0 %. The switch (live, training, export, site, baskets) is planned separately.
  - **Public name: Staple Signals, domain staplesignals.org** (owner, 2026-10-25). User-facing texts use it
    (`fpw.texts.SITE_NAME`); code, repositories, bundle and tables keep `food-price-watch` / `fpw`.
  - **Owner decision 2026-10-25: show everything that has data, conflict-affected areas included.** No hiding by
    location; `hidden.json` on the site is only for data-quality problems, with the owner's agreement.
  - Forecast rows carry `market_id`, `series_commodity_id`, `unit` (basket preparation; proposal in
    `docs/proposal-users-and-features.md`, not approved). Open data finding: runs of identical prices (Mali 16-30 %).

---

## About the user

- A .NET developer who just built a full data/ML project on Databricks (`sgrout/fx_medallion` on GitHub: medallion
  pipeline, walk-forward backtests, MLflow, LLM classification, Dash app, monitoring). Explain new concepts with .NET
  analogies and say *why*, not only *what*.
- Prefers small, verifiable steps, honest results (including negative ones), and a plain-English README section his
  non-technical wife can follow.
- The reference for structure, testing and lessons learned is the template
  `/Users/sgrout/Repository/Databricks/fx_medallion/docs/databricks-project-template.md` (local clone; the GitHub repo
  `sgrout/fx_medallion` is private) and the fx_medallion code itself (tags `phase-0` … `phase-7`). Reuse its patterns;
  don't re-derive them. The general rules are already included below; the template adds the Databricks-specific
  details (bundles, Free Edition limits, app and alert gotchas), which are needed only if Databricks is chosen as the
  platform.

## Why this project, and its limits

- WFP (World Food Programme) publishes monthly retail/wholesale food prices for thousands of markets as open data.
  A sharp rise in staple prices (maize, rice, sorghum, wheat flour, beans, oil) is an early sign of food insecurity.
- Large actors already analyse this: WFP HungerMap LIVE and its price-spike indicator (ALPS), FEWS NET. This project does
  **not** replace them. Its niche: **open, market-level, probabilistic forecasts with a published, honest track
  record**, in formats a small organization can use (simple pages, CSV/JSON, email alerts).
- Never present forecasts as certain. Every page shows the uncertainty band, the data date, the source, and the
  backtest track record for that kind of forecast. Link to WFP/FEWS NET for official assessments.
- No personal data is involved. Respect each dataset's license and attribution requirements (check on HDX; WFP data is
  typically CC BY-IGO: attribute WFP on every page and download).

## Data (verify everything on first ingestion; these are starting points, not facts)

- **WFP food prices on HDX** (Humanitarian Data Exchange, `data.humdata.org`, CKAN API, no key): per-country datasets
  (`wfp-food-prices-for-<country>`) with a CSV of all markets, plus a global dataset. Expected columns: `date, admin1,
  admin2, market, market_id, latitude, longitude, category, commodity, commodity_id, unit, priceflag, pricetype,
  currency, price, usdprice`. Check `priceflag` (actual vs aggregated vs forecast values: keep actual only, or flag),
  `pricetype` (Retail vs Wholesale: never mix in one series), and `unit` (KG, 50 KG, L, … : normalise per series, don't
  convert blindly).
- Optional drivers for later phases (each needs a reachability and license check first):
  exchange rates (local currency vs USD), fuel prices (WFP datasets often include them), rainfall/vegetation anomalies
  (e.g. CHIRPS, FEWS NET data portal), global commodity prices (FAO / World Bank pink sheet).
- **Publication lag matters.** Monthly prices appear weeks after the month ends, and old months get revised or filled
  in later. Store the ingestion date in bronze, and in backtests use only data that had been *published* by the forecast
  date (point in time), not only data *dated* before it.

## Domain pitfalls to design for

- Gaps: markets start, stop and skip months; commodities change names. A series needs a minimum history and recency
  before it gets a forecast; otherwise say "not enough data".
- Currency: many target countries have high inflation or devaluations. Forecast in **local currency** (what households
  pay), in log space; show USD only as context. Watch for redenominations (sudden 1000x level shifts → treat as a
  break, not a spike).
- Seasonality: lean seasons and harvests drive regular price cycles; a spike means *above the usual season*, not just
  "up". WFP's ALPS idea (price vs its seasonal trend) is a good reference definition and a natural baseline.
- Outliers and data-entry errors (an extra zero) are common: robust checks in silver, never silently "fix" values.
- Many series, little history each (monthly, often < 10 years): pooled models across markets/commodities with series
  features usually beat one model per series; baselines first.

## Product

- **Users:** analysts at small NGOs, local organizations, journalists, researchers. Assume English first; French matters
  for West and Central Africa (later phase).
- **Website (public, free, static):** a country page (map of markets, list of current warnings), a market/commodity
  page (history + forecast fan for 1–3 months ahead, probability of a spike, data date, source, track record), a
  methods page (plain English), and downloads (CSV/JSON of all current forecasts, versioned).
- **Alerts (later):** an RSS feed or email digest per country of series whose spike probability crossed a threshold.
- Accessibility: works on slow connections and phones (static pages, small payloads, no heavy JS framework).

## Platform: decide in Phase 0, with the user (decided: Databricks, see "Project" above)

Databricks Free Edition is meant for personal/learning use and its Apps always require a Databricks login, so it cannot
host the public site. Present these two options with trade-offs and let the user choose:

1. **GitHub Actions + DuckDB/Parquet + static site** (recommended default: free, public, small data): a scheduled
   workflow runs the pipeline in Python (DuckDB/pandas/Polars), stores bronze/silver/gold as Parquet (in the repo for
   small data, or object storage), and publishes the site to GitHub Pages (or Cloudflare Pages).
2. **Databricks (small paid workspace) for the pipeline** + the same static site: more practice with Databricks
   (bundles, Unity Catalog, MLflow, jobs) at a small monthly cost; the gold output is exported to the static site.

Whichever is chosen, keep the medallion layers, the logic/IO split and the tests identical, so moving later is cheap.

## Architecture rules (platform-independent)

- **Medallion:** bronze = raw downloads exactly as received (CSV/JSON text) + `_source`, `_source_url`, `_ingested_at`,
  append-only; silver = typed, normalised, deduplicated per business key (`country, market_id, commodity_id, pricetype,
  unit, date`), quality-checked; gold = forecasts, spike probabilities, track record, site data. Silver/gold writes are
  idempotent (merge/overwrite by key), so reruns are safe.
- **Logic vs I/O:** all logic in a Python package `src/fpw/` as pure functions (DataFrames in, DataFrames out) with
  tests; scripts/notebooks only handle parameters, paths/tables and writes.
- **Source outages:** parsers raise a typed `InvalidPayload` on anything that is not the expected format (error pages,
  empty files); the pipeline skips and logs it, keeps the last good data, and a freshness check fails loudly if a source
  stays stale. Every scheduled run notifies the user on failure.
- **Point in time:** features and backtests use only data published before the forecast date. Every feature gets a test
  that changes the future and asserts the past is unchanged.
- **Forecasts are distributions** (quantiles, e.g. 10/50/90 and 2.5/97.5) of the log price 1, 2 and 3 months ahead, plus a
  spike probability. Judge them on coverage, pinball loss and, for spikes, precision/recall and calibration of the
  probability.
- **Models:** baselines first (last value, seasonal naive, seasonal random walk / ETS, an ALPS-style seasonal-trend
  rule), then pooled ML (e.g. LightGBM quantile on log returns with series features). ML is used only if it beats the
  best baseline in a walk-forward backtest (refit per period on earlier data, purge overlap, choose on validation,
  check once on a holdout). Decide candidates up front; stop tuning when the backtest stops being a fair judge.
- **Track record:** store live forecasts before the outcome is known; publish coverage and spike-alert hit rates per
  country and horizon on the site.
- **Keep it explainable:** for each warning, show the main drivers in words (e.g. "above the seasonal norm for 3 months,
  fuel up 20%"), produced by code from the model inputs. If an LLM is used for text, it only rephrases provided facts and
  passes deterministic guardrails (no invented numbers).

## Testing

- `pytest`; tests use tiny hand-built frames with an obvious answer, plus trimmed copies of real downloads (including a
  broken/error payload) as fixtures in `tests/data/`.
- Test kinds that paid off before: no look-ahead, idempotency (rerun = same rows), parsers vs real/broken payloads,
  forecasts vs simulated series with known properties (calibration), statistical tolerances based on effective sample
  size, generated site data vs its schema.
- CI (GitHub Actions) runs the tests on every push and pull request.

## Working agreements

1. **Plan each phase** and present the choices that are the user's; start after approval.
2. **Branch per phase** (`phase-N-<name>`), one commit per step with numbers in the message when there are results,
   merge `--no-ff`, tag `phase-N`. Small fixes on their own short branch.
3. **Probe each source before building on it** (reachability from where the pipeline will run, license, a sample of
   the real format). Never work around an access control or rate limit; back off politely.
4. **Ask before irreversible or outward-facing actions** (deleting data, publishing the
   site, enabling emails).
   **The GitHub repository `sgrout/food-price-watch` is public** (since 2026-10-25): everything committed, including
   `docs/`, reviews and the git history, is public. Never commit secrets, tokens, signed URLs or personal data;
   redact real payloads before they become fixtures. Code is MIT (`LICENSE`); WFP data stays CC BY-IGO (`DATA_LICENSE.md`) and is
   attributed wherever it is stored (`tests/data/README.md`, `export/sample/README.md`, every export file).
5. **Report honestly:** what was verified, what was not, and negative results with numbers.
6. **Docs every phase:** README with a plain-English section first (what it does, how sure it is, what it is not), then
   technical documentation with results and gotchas; update this file when a convention changes.

## Phases (adjust with the user)

0. **Foundation:** platform decision, repo, `pyproject.toml` (Python 3.12), package `src/fpw/`, tests + CI, README skeleton.
1. **Ingest 2–3 pilot countries** (choose with the user, by data coverage: many markets, long monthly history, recent
   updates): bronze → silver with normalisation and quality checks; a data-coverage report per country.
2. **Baselines + walk-forward backtest** for 1–3 months ahead; spike definition (ALPS-style) and its baseline hit rate.
3. **Better models:** pooled quantile model with series and calendar features; drivers (exchange rate, fuel) only if they
   pass a point-in-time check and improve the backtest.
4. **Private Streamlit app** (Databricks App): country and market pages with fan charts, warnings, methods,
   attribution. Later, once the user chooses an export target: the public static website with downloads.
5a. **Public export** (done 2026-10-25). **Communication with the site agent goes through `docs/`** (`docs/README.md`):
   at the start of each session, check `docs/site-requests/` for open requests and `docs/site-status.md`; this side
   owns `site-brief.md`, `export-contract.md`, `site-content/`. Export details: weekly JSON/CSV export to a UC volume for the public static site on Vercel
   (built by a separate agent from `docs/export-contract.md`; no database). Changing an exported field means updating
   `fpw/export.py`, `scripts/export_schemas.py` (regenerate `export/schema/`), the contract and the sample together.
5. **Schedule + monitoring:** monthly (or weekly) runs, freshness checks, live track record, failure notifications.
6. **Scale and reach:** all WFP countries with enough data, French pages, RSS/email alerts; ask NGOs for feedback.

## First session: start here

1. Read this file (and the fx_medallion template at the local path above if Databricks is chosen); summarise the plan
   back in a few lines.
2. Ask the user for the platform choice (above) and the pilot countries, proposing a shortlist based on a quick,
   read-only look at HDX coverage.
3. Then do Phase 0 on branch `phase-0-foundation`.
