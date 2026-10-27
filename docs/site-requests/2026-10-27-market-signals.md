# Market signals: distance from the national price, markets that stopped reporting (export 1.4)

Status: done: site accepted 1.4 and built the pages; export switched to 1.4 on 2026-10-27 (data side)
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
(written by the site side, 2026-10-27)

**1. Schema 1.4 is accepted (live on `main`).** The site keeps the schemas per version (`schema/1.3`, `schema/1.4`)
and validates by `schema_version`, so 1.3 and 1.4 both pass. All new fields are optional on the site side; with a
1.3 export nothing new is shown. **You can switch the weekly export to 1.4.** The next Monday run (09:00 UTC)
picks it up, or I can run the update by hand after you say so.

Tested with the trial export (`public_export_next`, generated 2026-10-27T16:27): hashes, sizes and schemas pass;
2,803 pages build, all checks pass (budgets, links incl. the new methods anchors, attribution, CSP, the 10,510
key numbers), axe 0 violations, no horizontal scroll at phone width.

**2. Pages (built, also live; they appear as soon as the export is 1.4):**
- **Market × food page:** `signals.text` as is, right below the status. With `far_above_usual`: icon ↑ +
  "Far above the national price" / "Nettement au-dessus du prix national"; with `silence`: icon ○ + "No price since
  June 2026" / "Aucun prix depuis juin 2026". Other non-empty texts (the ordinary gap) are shown as a plain small
  line. Each has a link to the matching methods section. Neutral grey border, no status colours.
- **Chart:** `national_median[]` as a thin, solid neutral grey line (the usual level stays dashed), same axis,
  within the 2-year window; it is broken at months without a median. Legend: "National median (70 markets)", with
  `n_markets` from `national_gap`; where that is null (silent markets) "National median (at least 5 markets)".
  For a silent series the chart runs to the last median month, so the empty months after the last price show.
- **Silent series:** history, chart and table; the silence block replaces "Not enough data for a forecast". The
  irregular-reporting note is not shown for them (it talks about a forecast range they do not have).
- **Country page**, after the warnings: "Markets that stopped reporting" (market, region, last price month, months,
  links to each food page of that market) and "Far above the national price" (food, market, region,
  "+124 %" vs national median, usually "+60 %", number of markets; sorted by `gap_pct`). `n_markets` and
  `usual_pct` are read from the series files, because the index row has only `gap_pct` (§4.9: always show them).
  Each section has a one-line description ("This describes the data; it is not a warning") and a methods link.
  In the per-food tables, the far-above rows get the ↑ tag and silent rows show "○ No price since <month>" instead
  of "not enough data".
- `methods.*.md` and the fixed `range-note.fr.md` are re-copied.

**Notes:**
- The trial export lists more silent markets in Mali than the example in this request (also Nara, Amachach,
  Échelle, Gounanbougou, ...). The site shows what `silent_markets[]` says.
- French: the data texts in `signals.text.fr` use an apostrophe `'`, while the site's own French strings use `’`.
  Shown as is; aligning it is optional.

**Switch (data side, 2026-10-27):** bundle deployed and the export re-run: `public_export/latest.tar.gz` is now 1.4
(generated 2026-10-27T17:23:41, status beta, data up to 2026-08): 1,182 series (907 with a forecast), 29 far above
the national price, 16 silent markets with 94 series; hashes and 1.4 schemas verified; all 1,090 earlier series
unchanged in forecast, history, explanation and status. Please run the update by hand now (or let Monday's run take
it). The longer list of silent markets is correct: the example above named only some of them. The apostrophe in the
French data texts stays `'` for now (the same in all data texts); align on the site if you prefer.

**Live (2026-10-27):** the update workflow fetched export 1.4 (generated 2026-10-27T17:23:41), all checks passed,
and the signals are live on staplesignals.org (verified: Mali and Burkina Faso country sections, Tessalit silence
block in French, Musenyi far-above block and the "National median (70 markets)" line).
