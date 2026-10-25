# Reporting regularity per series (for a reliability note)

Status: accepted (export schema 1.2, 2026-10-25)
From: site agent, 2026-10-25

## Request
The owner chose not to hide markets in conflict-affected areas, but to show a visible note where a market reports
irregularly (the practical effect of insecurity, and the limit the methods text already names: "Markets in conflict
areas report less often, especially during crises"). The site must not compute this itself, so please add:

1. Per series (in `series/<id>.json` and the indexes): how many of the last 12 months have a published price, as of
   `data_up_to` (e.g. `months_reported_12`, integer 0-12), and, if you think it is the better signal, a ready flag
   such as `irregular_reporting: true|false` with the threshold stated in the contract.
2. In `track_record.json`: the backtest split by that flag (regular vs irregular), per horizon, with the same fields
   as `by_horizon`. Then the note's wording can rest on evidence, e.g. "In markets like this, the 80 % range held
   in 68 % of past cases (82 % elsewhere)", or be dropped if there is no difference.

The site will show a short note on the series page and a small marker (icon + text, not colour alone) in the country
lists. No numbers change.

## Example
```json
"reporting": {"months_reported_12": 5, "irregular": true}
```
Note text (site, en): "This market reported prices in 5 of the last 12 months. Prices here can change suddenly,
for example through insecurity or road closures; forecasts may be less reliable."

## Answer
Delivered in export 1.2 (contract §3):
1. `reporting {months_reported_12, irregular}` in `series/<id>.json`; `months_reported_12` and `irregular_reporting`
   in the indexes. `months_reported_12` = months with a published price in the 12 months up to `data_up_to` (data
   errors count: they were published). `irregular` = fewer than **9** of 12, the same 75 % bar as the eligibility
   rule; the threshold was fixed (owner decision) before looking at the split below.
2. `track_record.json`: `backtest.by_reporting.regular[]` and `.irregular[]` (same fields as `by_horizon`; eligible
   series, irregular status at each forecast date) plus `irregular_definition`.

**What the split shows** (holdout 2023+, `lgbm_cal`; irregular: 159 series, 45 forecast months):

| | 80 % range held, next month | in 3 months | typical error, next month | in 3 months |
|---|---|---|---|---|
| regular | 77 % (+-2.4) | 76 % (+-3.8) | 10 % | 15 % |
| irregular | 81 % (+-4.5) | 77 % (+-5.9) | 11 % | 19 % |

So the forecasts for irregular markets are **not shown to be less honest**: their ranges held about as often
(the difference is within the uncertainty). Their prices move more, so errors are larger and ranges wider. Suggested
note wording (state facts, avoid "less reliable"): "This market reported prices in 5 of the last 12 months. Prices
here can change more, for example through insecurity or road closures; the forecast range is wider accordingly."
Take the numbers from `track_record.json`, not from this file.

**Action for the site before Monday 09:00 UTC:** copy `export/schema/` (schema_version `1.2`) and `export/sample/`
(now 4 series, incl. an irregular market) into the site repository; the live export is already 1.2.
