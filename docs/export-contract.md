# Public export contract (v1.1): food-price-watch → public site

Audience: the agent or developer building the public site (Vercel). The site only consumes these files; it never
computes forecasts or changes numbers. The producing side is this repository (`src/fpw/export.py`,
notebook `src/08_export_public.py`). Machine-readable contract: JSON Schemas in `export/schema/` (draft 2020-12,
strict: unknown fields fail). Real sample files to build against offline: `export/sample/` (3 series).

## 1. What the project is (context for the UI)

Open, non-commercial early warning for staple food prices in Mali, Burkina Faso and Burundi (more countries later).
Per market and food: price history, a forecast range for the next months, a chance of a price spike, a short
explanation, and an honest track record. Users: analysts at small NGOs, local organisations, journalists, on phones
and slow connections. It is **not** an official assessment (WFP / FEWS NET are; link to them).

## 2. Where the files are and how to fetch them

Written weekly to a Unity Catalog volume on the Databricks workspace `https://dbc-101f908c-607f.cloud.databricks.com`:

| Path (volume `/Volumes/workspace/fpw_dev_gold/public_export/`) | Content |
|---|---|
| `latest.tar.gz` | the whole current export (~1.1 MB; ~10 MB unpacked, ~1,100 files) |
| `latest/manifest.json` | the current manifest only (to check whether anything changed) |
| `runs/<YYYY-MM-DD>.tar.gz`, `runs/<YYYY-MM-DD>/...` | every past export (kept) |

Fetch with the Databricks Files API (one HTTPS GET, bearer token):

```bash
curl -sSf -H "Authorization: Bearer $DATABRICKS_TOKEN" -o latest.tar.gz \
  "$DATABRICKS_HOST/api/2.0/fs/files/Volumes/workspace/fpw_dev_gold/public_export/latest.tar.gz"
tar -xzf latest.tar.gz -C public-data/
```

Recommended pipeline on the site side (GitHub Actions in the site repository, then Vercel deploys on push):
1. Schedule: Mondays 09:00 UTC (the Databricks pipeline starts 07:00 Europe/Amsterdam and finishes within ~1 h);
   also allow a manual run.
2. GET `latest/manifest.json`; if `generated_at` equals the committed one, stop.
3. GET `latest.tar.gz`, unpack to a temporary folder, **verify every file's `sha256` and `bytes` against
   `manifest.json`**, validate the JSON files against the schemas (copy `export/schema/` into the site repo).
4. Only if everything passes: replace the site's data folder and commit. On any failure: change nothing (the site keeps
   the last good data and its date) and fail the workflow so its owner is emailed.

Secrets (GitHub repository secrets): `DATABRICKS_HOST` and `DATABRICKS_TOKEN` (a personal access token of the
workspace owner; Free Edition has no service principals for CI; tokens expire, so note the expiry date). The token is
used only in CI, never in the browser or in the built site.

## 3. Files

All JSON is UTF-8, compact. Months are `"YYYY-MM"`. Prices are **nominal, in local currency per `unit`** (XOF for
Mali and Burkina Faso, BIF for Burundi; units such as `KG`, `L`, `100 KG`), already converted from the model's log
scale. Every JSON file has `schema_version` (`"1.1"`) and `attribution`.

Changes in 1.1 (2026-10-25): `status` is `null` for series without a forecast (`eligible: false`), in
`series/<id>.json` and the indexes; the display and rounding rule below is part of the contract.

### Display and rounding (shared by the texts and the site)
Exported precision: prices 2 decimals, probabilities 3 decimals. The `explanation` texts are generated from exactly
these exported values. Display both with **round-half-even** on the exported value (Python `round`/`format`;
JavaScript `Intl.NumberFormat` with `roundingMode: 'halfEven'`):
- prices: 0 decimals from 100, 1 decimal from 10 to 100, 2 decimals below 10 (thousands separator per locale);
- percentages: a whole number of 100 x the exported probability (0.125 -> 12 %, 0.135 -> 14 %);
- integer fields (`level_vs_usual_pct`, counts) as they are.
Then a page and its explanation never show two different numbers for the same value.

| File | Use |
|---|---|
| `manifest.json` | `status` (`preview` / `published`), `generated_at`, `forecast_origin`, `data_up_to`, `model_version`, counts, license, sources, disclaimer, list of all files with `bytes` and `sha256` |
| `countries.json` | one entry per country: name, currency, number of series and markets, `status_counts` (**series with a forecast only**, i.e. `eligible: true`; the same as counting `index/<country>.json` rows with `eligible: true`), latest month |
| `index/<country>.json` | the series of one country (for country pages; 120-160 KB, compresses to ~20-30 KB) |
| `index.json` | all series (~410 KB): use for search or build time only, not on phone pages |
| `series/<id>.json` | one market × food: identity, location, status, explanation, `history`, `forecast` |
| `track_record.json` | how often past forecasts were right, per horizon and per country (backtest; live once available) |
| `downloads/forecasts_<YYYY-MM-DD>.csv` + `downloads/README.txt` | the CSV download for users, with attribution |

### Series ids
`<country>-<market_id>-<commodity_id>-retail-<unit>`, e.g. `mali-1816-73-retail-kg`. Stable across runs (names may
change; ids do not). Suitable for URLs: `/mali/mali-1816-73-retail-kg`.

### `series/<id>.json` fields
- `country {id, name}`, `market {id, name, admin1, admin2, latitude, longitude}`, `commodity {id, name, group}`,
  `unit`, `currency`, `price_type` (`retail`).
- `eligible`: `true` if the series has enough data for a forecast. If `false`: `forecast` is `[]` and `explanation`
  is `{}`; show the history with the text "Not enough data for a forecast".
- `status {code, level_vs_usual_pct, month}`: the latest observed price vs the usual level for that time of year.
  `code`: `normal` < `stress` < `alert` < `crisis` (ALPS-style thresholds). `level_vs_usual_pct` may be negative.
  **`null` when `eligible` is false**: without enough data the usual level is unreliable, so such a series gets no
  status badge, is not listed among warnings and is not counted; show "Not enough data for a forecast".
- `explanation.en`: ready-made plain text, generated from the numbers (no LLM). Show as is. More languages will be
  added as more keys (`fr`), so choose the key by the page language and fall back to `en`.
- `dates {forecast_origin, data_up_to, last_observed_month, run_at, model_version}`: a forecast made in
  `forecast_origin` uses only prices published by then, i.e. up to `data_up_to` (two months earlier: WFP publishes
  with a lag).
- `history[]`: `{month, price, flag}`; `flag` is `null`, `data_error` (a value that jumped and reversed; the model
  does not use it: draw it as a separate marker, not on the line), `break` (a lasting jump, e.g. a unit change), or
  `unconfirmed_jump` (a big move in the latest month: may be a real spike, judged next month).
- `forecast[]` (5 entries, `step` 1-5): `month`, `horizon`, the quantiles `p025 p10 p50 p90 p975`, `usual_level`,
  `spike_threshold`, `spike_probability`, `show_spike_probability`.
  - `horizon`: `nowcast_last_month` and `nowcast_this_month` (months not yet published), then `next_month`,
    `in_2_months`, `in_3_months`. Label the first two as estimates of the recent past, not forecasts.
  - `p10`-`p90` = **80 % range** ("8 in 10 chance"), `p025`-`p975` = 95 % range, `p50` = most likely.
  - `usual_level` = the usual level for that month (seasonal trend); `spike_threshold` = the level above which the
    month counts as a spike.

### `track_record.json`
`backtest.by_horizon[]` and `backtest.by_country.<country>[]`: per `step`/`horizon`: `n`, `coverage80` (share of
cases where the real price fell inside the 80 % range; ideal 0.80), `coverage95`, `typical_error_pct`,
`new_spike_score` vs `base_rate_score` (Brier scores, lower is better) and `new_spike_verdict`
(`better` / `no_better` / `worse` than just using how often new spikes happen). `live.by_horizon[]` is empty until the
first live forecasts mature (about January 2027); then show live next to backtest.

## 4. Rules the site must follow (honesty and license)

1. **Never invent or recompute numbers.** Format them (thousands separators, rounding), nothing else.
2. **Every forecast shows its range**, the data date (`data_up_to`) and a link to the track record. Never show `p50`
   alone. Show the **80 % range prominently**; the 95 % range lightly or not at all (its tails are loose: in ~8 % of
   series the 3-month `p025` is below 40 % of the last price).
3. **Spike chance only where `show_spike_probability` is true** (currently next month only): further ahead, warnings
   of new spikes scored *worse* than the base rate. Next to it: "Warnings of new spikes have no proven skill yet."
4. **Status** always as icon + label, never colour alone.
5. **Attribution on every page and in every download**: the `attribution` string (WFP via HDX, CC BY-IGO), plus the
   `disclaimer` (not an official assessment; links to WFP HungerMap and FEWS NET).
6. **`manifest.status == "preview"`**: the data is not approved for publication. Deploy only to a preview / password-
   protected environment, or show a clear "preview, not for use" banner. The project owner switches to `published`.
7. Prices are nominal local currency; do not convert to USD (an exchange-rate forecast would be needed).
8. Conflict-affected markets: a publication policy is pending (question to WFP). Build the UI so that a market or
   country can be hidden from a config list without code changes.

## 5. Practical constraints

- Users on phones and slow connections: static pages, small payloads, no heavy JS framework; pre-render pages at
  build time from the JSON; small charts (SVG or a light library); per-country index on country pages.
- Updated weekly; forecasts change once a month (new `forecast_origin`), the rest of the month only if WFP revises data.
- Versioning: `schema_version` changes when a field changes meaning or disappears; new optional fields may be added
  with a schema update in this repo. Check `schema_version` in CI and fail on an unknown major version.

## 6. Contact / change process

Changes to the contract are made in this repository (`src/fpw/export.py`, `scripts/export_schemas.py`, this file)
and released with the weekly export; the schemas in `export/schema/` are the source of truth. The site side asks for
changes through `docs/site-requests/` (see `docs/README.md`); site requirements are in `docs/site-brief.md`.
