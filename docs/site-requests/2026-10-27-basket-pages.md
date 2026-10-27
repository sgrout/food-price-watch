# Food-basket pages: one page per market (owner decision)

Status: open (for the site side to build)
From: data side, 2026-10-27, on the owner's decision

## Request
The owner decided (2026-10-27) to show the food basket on the site, as a **separate basket page per market**. Data:
the basket export (contract §4b, schemas `export/schema/basket_*.schema.json`, real sample `export/sample-baskets/`).
The page is also listed in `site-brief.md` §3, and the chart in §6. The same non-negotiables, budgets, accessibility
and checks apply as for the item pages.

### 1. Data flow
- Fetch `public_export/baskets/latest.tar.gz` **separately** from the item export (Mondays 09:30 UTC; the basket job
  runs after the item pipeline). Verify sha256 and the `basket-1.0` schemas the same way.
- If the basket fetch or check fails, keep the last good basket data and **do not block the item update**. Without
  any basket data, build the site without basket pages or links.
- Use the basket manifest's `status` for the beta banner, and its `generated_at` for the stale-data banner, on
  basket pages.

### 2. Basket page `/<country>/<basket-id>/` (and `/fr/...`)
`<basket-id>` is the `id` from the export, e.g. `burundi-1826-basket-ration_v1`. Content, top to bottom:
1. Title: "Food basket in <market>" / "Panier alimentaire à <market>", with the country; under it the unit:
   "<currency> per person per month" / "<currency> par personne et par mois". The region (`admin1`) is not in the
   basket file; take it from any item series with the same `market.id`, or leave it out.
2. Data date: `dates.last_observed_month`, plus the forecast month and `data_up_to`, as on the item pages.
3. `explanation.en` / `explanation.fr`, rendered as is (the numbers in it are the exported ones, as for items).
4. Composition: a short list from `basket.components[]`, e.g. "12 kg millet" (French: `commodity_fr` and a decimal
   comma, e.g. "1,8 kg"). If `basket.missing` is not empty, show it visibly, e.g. "Not included: cooking oil (WFP has
   no long enough price series for it here)". Always show "A simple ration-based basket made by Staple Signals, not
   an official minimum expenditure basket", linked to the basket paragraph on the methods page.
5. The next-month and 3-month 80 % ranges (`forecast[]` with `horizon` `next_month` and `in_3_months`).
6. The fan chart (brief §6): 2 years of `history[].cost` plus the forecast fan; no usual-level line, no flag markers.
7. Table view: the forecast (all 5 rows) and the full history.
8. Track record: from `track_record.json`, `backtest.by_country[<country>]` (fallback `by_horizon`), the same wording
   as for items: "In tests on 2023 onwards, the 80 % range held x % of the time". Show `live` once it has rows.
9. Attribution (manifest `attribution` / `attribution_fr`) and the disclaimer.

`eligible: false` (about 87 of 267 baskets): history, chart and table only, plus "Not enough data for a forecast",
as on the item pages. No status badge and no spike chance on any basket page: baskets have neither.

### 3. Country page
A new section "Food basket" / "Panier alimentaire", after the item warnings: one row per market from
`index/<country>.json`, sorted by market name, with columns market, last cost (with its month) and next-month 80 %
range (or "no forecast"). Each row links to the basket page. One line above the table names the basket contents
for that country (from any basket's components) and what is missing. Plain HTML; no JS needed.

### 4. Links from item pages
On each market × food page, if a basket exists for the same `market.id`, add a link "Food basket in this market" /
"Panier alimentaire de ce marché".

### 5. Track record page
A short section "Food basket" from `track_record.json` (per horizon and per country), worded as the item section.
Say that these are basket costs, so they cannot be compared directly with the item numbers.

### 6. Rules to keep
- **Never compare countries.** The baskets differ by country (Burundi: full ration; Burkina Faso: no oil; Mali:
  millet only) and so do the currencies. Within a country, comparing markets is fine.
- No recomputing: show exported numbers only (contract §3 display rule).
- No transfer-value calculator ("a transfer of X covers y %") in this version.
- No new heavy dependencies; basket pages stay within the item-page budgets.

## Example
Sample files: `export/sample-baskets/basket/burundi-1826-basket-ration_v1.json` (full ration),
`burkina-faso-1043-basket-ration_v1.json` (oil missing) and `mali-1682-basket-ration_v1.json` (millet only).
Expected page count: about 267 basket pages per language, so the build grows by about 534 small pages.

Note on the Burkina Faso sample: Namouno (CBM) reports cereal prices of 63-64 XOF/kg since May 2026, about a third
of other markets (millet 185-204 XOF/kg in August). The basket sum is correct for those prices; the data side is
looking at whether the prices are plausible. Show it as exported for now.

## Answer
(written by the site side: when it is built, set `Status: accepted` with the site commit, or ask questions here)
