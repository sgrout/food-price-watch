# Food-basket pages: one page per market (owner decision)

Status: accepted (built 2026-10-27); questions answered by the data side 2026-10-27
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
Built as described (site repo `sgrout/food-price-watch-web`, 2026-10-27):
- §1 Separate workflow `update-baskets.yml` (Mondays 09:30 UTC; serialised with the item update): sha256, size and
  `basket-1.0` schemas checked; a failure keeps the last good basket data and never touches the items. Without basket
  data, or with a basket status other than `beta`/`published` (contract §4.6), the site has no basket pages or links.
  Basket pages use the basket manifest's status, `generated_at` and attribution.
- §2 Basket page `/<country>/<basket-id>/` and `/fr/...` (267 per language), all items 1-9; no status, no spike
  chance; `eligible: false` = history, chart and table plus "Not enough data for a forecast".
- §3 Country page section, §4 link on item pages, §5 track record section, §6 rules kept (no country comparison:
  "compare markets within this country only" on the country page).
- Checks: 2,733 pages within budget (largest 16.4 KB gzip); 10,520 key numbers on 2,350 item and basket pages match
  their explanations; axe 0 on item and basket pages, light and dark.

**Questions**
1. **Observed months after `data_up_to`.** 66 of 267 baskets (58 Burkina Faso, 8 Burundi) have
   `dates.last_observed_month` and a `history[]` entry for **2026-09**, while `data_up_to` is 2026-08 and the item
   series of the same markets end in 2026-08. The forecast also starts at 2026-09 (`nowcast_last_month`), so that month
   is both observed and estimated. Example: `burkina-faso-1043-basket-ration_v1` (history ... 2026-08 964.2,
   2026-09 951.6; explanation "cost about 952 XOF in September 2026"), while `burkina-faso-1043-73-retail-kg` has
   `last_observed_month` 2026-08. The page now says "Basket cost up to September 2026; prices up to August 2026".
   Is the September cost intended (from newer item prices than the item export uses)? If not, please align.
2. **Baskets in markets without item series.** 47 baskets (e.g. `mali-878`, `mali-11720`, `mali-8715`) have no item
   series with the same `market.id` in the item export; Mali has 136 baskets but 90 markets with items. Their pages
   show no region and no item page links to them. Intended (the basket needs fewer months than the item eligibility
   rule?), or should the item export include those markets?

Small: the methods text has the basket paragraph but no heading, so the site links to `/methods/` (not to the
paragraph). A heading (e.g. `### Food basket`) would give the link an anchor.

**Answers (data side, 2026-10-27)**
1. **Observed months after `data_up_to`: intended to keep, now consistent.** September 2026 is real: WFP published
   it early for most Burkina Faso and some Burundi markets. The **item files have it too**: 291 Burkina Faso and 45
   Burundi series have a 2026-09 entry in `history[]`, but their `last_observed_month` is set to `data_up_to` (what the
   forecast used). The basket export took the real last month instead; it now follows the item rule:
   `last_observed_month` and the explanation use the last month up to `data_up_to` (Namouno: "964 XOF in August
   2026"); `history[]` keeps the later months. Contract §4 now says this for both exports. For the site (items and
   baskets alike): draw a month after `data_up_to` as an observed point; the fan starts at `last_observed_month`;
   keep the `nowcast_last_month` estimate visible (it is the estimate made without that price). Your page text
   "prices up to August 2026" can stay; the line "basket cost up to September 2026" is no longer needed. The methods
   text explains it ("Which data a forecast uses", last two sentences).
2. **Baskets without item series: not intended, fixed.** The basket export took every market that ever had the
   foods, including stopped markets (last price 2012-2025, some with one month). A basket is now exported only if all
   its foods are series in the item export, so every basket market has item pages and a region: **211 baskets**
   (was 267; 180 with a forecast, unchanged; Burkina Faso 60, Burundi 70, Mali 81). Export regenerated on Databricks
   2026-10-27T14:47 (hashes and `basket-1.0` schemas verified; schema unchanged); sample `export/sample-baskets/`
   regenerated. Pages for the 56 dropped ids disappear on your next basket fetch.
3. **Methods anchors:** every section of `site-content/methods.{en,fr}.md` is now a `##` heading (the bold lead-ins
   are gone), e.g. "## Food basket" / "## Panier alimentaire"; link to its anchor. Please re-copy both files.

Status after these answers: accepted on the site side; the data side has nothing open here.
