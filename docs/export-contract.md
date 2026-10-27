# Public export contract (v1.5): food-price-watch → public site

Audience: the agent or developer building the public site (Vercel). The site only consumes these files; it never
computes forecasts or changes numbers. The producing side is this repository (`src/fpw/export.py`,
notebook `src/08_export_public.py`). Machine-readable contract: JSON Schemas in `export/schema/` (draft 2020-12,
strict: unknown fields fail). Real sample files to build against offline: `export/sample/` (4 series); basket schemas: `export/schema/basket_*.schema.json`.

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
Mali, Burkina Faso and Niger, BIF for Burundi; units such as `KG`, `L`, `100 KG`), already converted from the model's log
scale. Every JSON file has `schema_version` (`"1.5"`) and `attribution`.

Changes in 1.5 (2026-10-27): country ids are any HDX slug (`^[a-z]+(-[a-z]+)*$`) instead of a fixed list, so a new
country needs no schema change; first new country: **Niger** (`niger`, XOF). `countries.json` entries gain `note`
(`{en, fr}` or `null`): a fixed text about that country's track record, to show on its country page (Niger: ranges too
narrow in its 2024-2025 shocks). The basket export moves to `basket-1.1` for the same country-id change. Nothing else
changes. Rollout as for 1.4: the site accepts 1.5 / basket-1.1 first; then the data side adds Niger to the exports.

Changes in 1.4 (2026-10-27, additive): market signals (owner's idea). Series files gain `signals` and
`national_median[]`; index rows gain `gap_pct`, `far_above_usual`, `silent_months`; `countries.json` entries gain
`reference_month`, `far_above_usual` (count) and `silent_markets[]`. **Series of markets that stopped reporting stay
in the export** (`eligible: false`, `status: null`, history only) instead of disappearing (94 series in 16
markets in 2026-10). Nothing else changes: the forecasts, explanations and statuses of the other series are the same
as in 1.3. Rollout: the site accepts 1.4 first; the data side switches only after that.

Changes in 1.3 (2026-10-25): `manifest.status` can be `beta` (public, with a beta banner; see §4.6).

Changes in 1.2 (2026-10-25): French (`explanation.fr`, `commodity.name_fr` / `commodity_fr`, `attribution_fr` and
`disclaimer_fr` in the manifest, bilingual `downloads/README.txt`, `docs/site-content/*.fr.md`); reporting regularity
(`reporting` in series files, `months_reported_12` and `irregular_reporting` in the indexes,
`track_record.backtest.by_reporting`); half-even on the exact decimal value (below).

Changes in 1.1 (2026-10-25): `status` is `null` for series without a forecast (`eligible: false`), in
`series/<id>.json` and the indexes; the display and rounding rule below is part of the contract.

### Display and rounding (shared by the texts and the site)
Exported precision: prices 2 decimals, probabilities 3 decimals. The `explanation` texts are generated from exactly
these exported values. Display both with **round-half-even on the exact decimal value as exported** (94.55 -> 94.6;
Python `Decimal(str(x))` with `ROUND_HALF_EVEN`; JavaScript `Intl.NumberFormat` with `roundingMode: 'halfEven'`):
- prices: 0 decimals from 100, 1 decimal from 10 to 100, 2 decimals below 10 (thousands separator per locale);
- percentages: a whole number of 100 x the exported probability (0.125 -> 12 %, 0.135 -> 14 %);
- integer fields (`level_vs_usual_pct`, counts) as they are;
- locale: English `1,250` / `45.2` / `12%`; French `1 250` / `45,2` / `12 %` with a narrow no-break space (U+202F)
  as thousands separator and before `%` and `:` (as `Intl.NumberFormat('fr-FR')` does).
Then a page and its explanation never show two different numbers for the same value.

| File | Use |
|---|---|
| `manifest.json` | `status` (`preview` / `published`), `generated_at`, `forecast_origin`, `data_up_to`, `model_version`, counts, license, sources, `attribution(_fr)`, `disclaimer(_fr)`, `missing_translations`, list of all files with `bytes` and `sha256` |
| `countries.json` | one entry per country: name, currency, number of series and markets, `status_counts` (**series with a forecast only**, i.e. `eligible: true`; the same as counting `index/<country>.json` rows with `eligible: true`), latest month; 1.4: `reference_month`, `far_above_usual` (number of series), `silent_markets[] {market_id, market, admin1, months, last_reported_month}` (longest silence first) |
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
- `explanation.en`, `explanation.fr`: ready-made plain text, generated from the numbers (no LLM; the same facts in
  both languages). Show as is; choose the key by the page language and fall back to `en`. French uses WFP's ALPS
  terms (normal, stress, alerte, crise) and "flambée des prix" for a spike. The French texts were not reviewed by a
  native speaker (owner decision).
- `commodity.name_fr` (indexes: `commodity_fr`): French food name. If a WFP name has no translation yet it equals
  the English name and is listed in `manifest.missing_translations`.
- `reporting {months_reported_12, irregular}`: in how many of the 12 months up to `data_up_to` a price was published,
  and `irregular` = fewer than 9 (the same 75 % bar as the eligibility rule). Show a note and a marker (icon + text)
  for irregular markets; wording per `track_record.backtest.by_reporting` (below).
- `dates {forecast_origin, data_up_to, last_observed_month, run_at, model_version}`: a forecast made in
  `forecast_origin` uses only prices published by then, i.e. up to `data_up_to` (two months earlier: WFP publishes
  with a lag). `last_observed_month` is the last month with a price up to `data_up_to` (what the forecast and the
  explanation use).
- `history[]` contains every published month, so it can go **beyond `data_up_to`** where WFP published faster
  (2026-10: September prices in most Burkina Faso and some Burundi series). Such a month is a real observation the
  forecast did not use yet: draw it as an observed point; the fan still starts at `last_observed_month`, and the
  `nowcast_last_month` estimate for that month stays visible (it is the estimate made without that price).
- `signals` (1.4; facts at `data_up_to`, **not forecasts**: no proven skill, never call them warnings):
  - `national_gap {month, pct, usual_pct, n_markets, far_above_usual}` or `null`: the price vs the national median
    of the same food and unit (median over the markets with a price that month, `n_markets` >= 5), in %; `usual_pct`
    = the market's usual gap (median over the 36 months before; `null` with fewer than 12). `far_above_usual` = at
    least 25 % above the national median **and** clearly above its own usual gap (rule fixed before looking at
    results). `null` for a silent market and for an old price (more than one month before the reference month).
  - `silence {months, last_reported_month, reference_month}` or `null`: the market has published **no price for any
    food** for `months` (>= 2) months, counted from the country's `reference_month` (the latest month most of its
    markets reported, so WFP's late publication does not look like silence). Listed for 2-24 months.
  - `text.en` / `text.fr`: ready-made text from these facts (empty string when there is nothing to say). Show as is,
    near the status; it already names the caveats (data error, other reasons for missing data).
- `national_median[]`: `{month, price}` for the last 36 months up to `data_up_to` (months with >= 5 markets), for a
  second, neutral line on the chart (same unit and currency; never a second axis).
- `history[]` entries: `{month, price, flag}`; `flag` is `null`, `data_error` (a value that jumped and reversed; the model
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
`backtest.by_reporting.regular[]` / `.irregular[]`: the same rows for eligible series split by reporting regularity at
the forecast date (`irregular_definition` says the rule), so a note on irregular markets can state the evidence.

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
6. **`manifest.status`** decides what may be public (the export sets it; the site follows it):
   - `preview`: not approved for publication; protected preview deployments only, "Preview: not for use" banner.
   - `beta` (owner's go, 2026-10-25): public at staplesignals.org with a **beta banner on every page**, linked to the
     track record: "Beta: experimental forecasts. The live track record has only just started; use them alongside
     the official assessments of WFP and FEWS NET." / "Bêta : prévisions expérimentales. Le suivi en conditions
     réelles vient tout juste de commencer ; utilisez-les avec les évaluations officielles du PAM et de FEWS NET."
   - `published`: no banner. Only the owner moves the export from `beta` to `published`.
   If the site receives a status it does not know, it must treat it as `preview`.
7. Prices are nominal local currency; do not convert to USD (an exchange-rate forecast would be needed).
8. Conflict-affected markets (owner decision, 2026-10-25): **shown like every other market; everything that has
   data is shown.** Keep the config list for hiding a market or country (empty by default); it is meant for
   data-quality problems found later, never for hiding a place because of where it is.
9. **Market signals (1.4) are descriptions, not warnings.** Show them with icon + text, never colour alone, and
   without the alert/crisis colours of the status. Always show `n_markets` and the usual gap with a gap, and the
   `text` (it names the caveats). A market that stopped reporting is shown with its last prices and "No price since
   <month>", never hidden.

## 4b. Basket export (optional, separate; schema `basket-1.1`)

Next to the item export, a weekly job (`fpw_basket`, Mondays 08:30 Europe/Amsterdam, after the item pipeline) writes
food-basket cost forecasts to `/Volumes/workspace/fpw_dev_gold/public_export/baskets/` (`latest.tar.gz`,
`latest/manifest.json`, `runs/<date>...`). It is optional: if it fails or is late, the item export is unaffected;
fetch, verify (hashes, schemas `export/schema/basket_*.schema.json`) and deploy it separately. Recommended fetch:
Mondays 09:30 UTC.

**What a basket is.** Ours: a simple ration-based basket for one person for one month (WFP general ration:
12 kg cereal, 1.8 kg pulses, 0.75 L oil), **not an official minimum expenditure basket** (MEB). Per country only
what WFP monitors long enough: Burundi full ration (cassava flour, beans, palm oil); Burkina Faso millet + niébé
(WFP publishes no oil prices there); Mali and Niger millet only (the cereal part). `basket.missing` lists what is not included;
always show it. Compare baskets within a country, not across countries.

Files: `manifest.json` (status, dates, counts, attribution(_fr), disclaimer(_fr), files with sha256),
`index/<country>.json` (per basket: market, eligible, components, last cost, next-month range),
`basket/<id>.json` (`basket.components[]` with `commodity_fr`, `missing[]`, `history[]` of `{month, cost}`,
`forecast[]` with `p025 p10 p50 p90 p975` in local currency per person-month, `explanation.en/fr`),
`track_record.json` (backtest per horizon and per country; live once matured). Ids:
`<country>-<market_id>-basket-<basket_id>`. A basket is exported only if all its foods are series in the item
export, so every basket market has item pages (region from them). `last_observed_month` and the explanation use the
last month up to `data_up_to`; `history[]` keeps later published months, as for items (§4).

Rules: the same as §4 (ranges, data date, attribution, no recomputation, beta banner). No spike chance for baskets.
`eligible: false` = some item lacks enough data at the forecast date: history only, no forecast. A
"transfer value covers x %" calculator is **not** part of this version.

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
