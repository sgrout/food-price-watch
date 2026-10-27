# Market signals: distance from the national price, markets that stopped reporting (export 1.4)

Status: open (for the site side: first accept 1.4, then build)
From: data side, 2026-10-27, on the owner's ideas and decisions

## Request
Two signals that national averages hide, especially in blockaded or cut-off areas (owner's ideas):
1. **Distance from the national price**: a market's price vs the national median of the same food.
2. **Markets that stopped reporting** for 2+ months: shown explicitly instead of quietly dropped (until now a series
   without a price for 3+ months disappeared from the export, and so its page from the site).

Both are in the **item export as schema 1.4** (additive; contract §3 "Changes in 1.4", the `signals` and
`national_median` fields, rule §4.9; schemas `export/schema/`, sample `export/sample/` with a silent and a
far-above series). Forecasts, explanations and statuses of all other series are unchanged (verified on a trial run:
all 1,090 current series identical in forecast, history, explanation and status).

**Rollout (please keep this order):**
1. Accept schema 1.4 next to 1.3 (copy the schemas; keep 1.3), and handle the new fields being absent in 1.3.
2. Tell us here (Answer) when that is live. **The data side switches the export to 1.4 only after that**: until
   then the weekly export stays 1.3. A trial 1.4 export of today is in the volume `fpw_dev_gold.public_export_next`
   (`latest.tar.gz`; not for the live site) if you want to test with full data: 1,182 series, 1.5 MB.
3. Then build the pages below.

**Pages:**
- **Market × food page:** `signals.text` (en/fr) as a short block near the status, with an icon + text label
  ("Far above the national price" / "Nettement au-dessus du prix national" when `far_above_usual`; "No price since
  <month>" / "Aucun prix depuis <mois>" when `silence`). On the chart: `national_median[]` as a second, neutral grey
  line labelled "National median (n markets)" / "Médiane nationale (n marchés)", same axis, in the 2-year window.
- **Silent series** (`signals.silence` not null; `eligible: false`, `status: null`): history, chart and table; instead of
  "Not enough data for a forecast", show the silence text. They must not count in `status_counts` (they do not).
- **Country page:** two short sections after the warnings:
  - "Markets that stopped reporting" / "Marchés qui ont cessé de publier": from `countries.json`
    `silent_markets[]` (market, region, last month, months), linking to the market's pages.
  - "Far above the national price" / "Nettement au-dessus du prix national": index rows with
    `far_above_usual: true`, sorted by `gap_pct`, with the food and the gap ("+92 % vs national median").
  - Both with one line saying what they are (a description of the data, not a warning) and a link to the methods
    sections "Distance from the national price" and "Markets that stopped reporting" (re-copy `methods.*.md`).
- **Rules** (contract §4.9): no alert/crisis colours for signals, icon + text, always show the number of markets and
  the usual gap; never hide a silent market.

## Example
Today (data up to August 2026):
- **Silent:** 16 markets (Mali 15: Diondiori and Kikara 19 months, the Mopti markets of Diafarabé, Djenné, Gathi
  Loumo, Tenenkou 8 months, Annefif, Kidal and Tessalit in Kidal region 2 months; Burkina Faso: Markoye 6
  months), with 94 series.
- **Far above the national price:** 29 series. Examples: Diapaga maize +124 % (usually +60 %), Gayéri millet +92 %
  (usually +12 %), Forgho millet +98 % (usually +33 %), Adjelhoc wheat flour +200 % (usually +20 %).
- **Sample:** `export/sample/series/mali-2023-58-retail-kg.json` (Tessalit, silent since June 2026) and
  `burundi-1827-74-retail-kg.json` (Musenyi cassava flour, +33 % vs usually +7 %).

## Answer
(written by the site side)
