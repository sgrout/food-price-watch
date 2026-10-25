# Reporting regularity per series (for a reliability note)

Status: open
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
(written by the data side)
