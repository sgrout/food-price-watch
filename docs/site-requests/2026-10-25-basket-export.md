# New, optional: food-basket export

Status: answered (data side, 2026-10-25)
From: data side

## Request
(No request: a new, optional data set for the site.)

## Answer
A weekly basket export now exists next to the item export (contract §4b, schemas `export/schema/basket_*.schema.json`,
sample `export/sample-baskets/`). It is fetched separately (`public_export/baskets/latest.tar.gz`, Mondays after
08:30 Amsterdam; suggest 09:30 UTC); if it is missing or fails validation, keep the last good one and leave the item
pages unaffected.

What it is: the monthly cost of a simple ration-based staple basket for one person per market, **ours, not an
official minimum expenditure basket**, with only the foods WFP monitors long enough (Burundi full ration; Burkina Faso
millet + niébé; Mali millet only; `basket.missing` says what is left out: always show it). 267 baskets, 180 with a
forecast; texts in English and French; backtest track record: the 80 % range held 77 % next month, 76 % in 3 months.

Suggested UI (owner to confirm): a "Food basket" section on the market page and a basket list on the country page,
with the same rules as items (range, data date, track record link, beta banner, attribution). No spike chance and no
transfer-value calculator in this version.
