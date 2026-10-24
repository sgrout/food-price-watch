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

**Where it stands.** *Phase 0 (foundation) is done:* the project skeleton exists, and we checked that the data can be
downloaded automatically for the three pilot countries: **Mali, Burkina Faso and Burundi**. There are no forecasts
yet.

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

### How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"   # Java 17 needed for PySpark
.venv/bin/pytest

databricks bundle validate --strict -t dev --profile Fx-Workspace
databricks bundle deploy -t dev --profile Fx-Workspace
databricks bundle run fpw_probe -t dev --profile Fx-Workspace
```

Clean-up: `databricks bundle destroy -t dev --profile Fx-Workspace` removes the jobs.
