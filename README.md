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
  forecasts (about 1 in 300 prices is marked this way).
- In December 2025 WFP renamed "Beans" in Burundi to "Beans (yellow)". We link the two so the 20-year bean history is
  not lost, and the computer checks that the price level really stays the same at the switch.
- The newest month is always incomplete for a while: prices appear on the website one to two and a half months
  after the month they describe. Forecasts will only use what was actually available at the time.

**How much is usable.** A food in a market needs at least 5 years of mostly complete, recent prices before we will
forecast it. That gives **909 series**: Mali 244, Burkina Faso 291, Burundi 374 (maize, millet, sorghum, rice, beans,
cassava flour, cooking oil).

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

### How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"   # Java 17 needed for PySpark
.venv/bin/pytest

databricks bundle validate --strict -t dev --profile Fx-Workspace
databricks bundle deploy -t dev --profile Fx-Workspace
databricks bundle run fpw_pipeline -t dev --profile Fx-Workspace          # weekly on its own; this runs it now
databricks bundle run fpw_pipeline -t dev --profile Fx-Workspace --only gold_coverage   # one task
```

Rebuild silver from bronze (all files are kept in the volume): drop `fpw_dev_silver.wfp_price_versions` and run the
pipeline; every `new` snapshot in the fetch log is applied again in order.

Clean-up: `databricks bundle destroy -t dev --profile Fx-Workspace` removes the jobs; the schemas `fpw_dev_*` (and the
volume with the raw files) need `DROP SCHEMA ... CASCADE`.
