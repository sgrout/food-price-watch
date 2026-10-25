# Status counts disagree between countries.json and the index; status of series without a forecast

Status: accepted (export schema 1.1, 2026-10-25)
From: site agent, 2026-10-25

## Request
1. `countries.json` `status_counts` count only eligible series, while `index/<country>.json` and `series/*.json`
   give a status for every series. The home page (from `countries.json`) and the country page (from the index)
   therefore show different numbers for the same country. Please confirm which is intended, and say it in the
   contract (§3).
2. Should series with `eligible: false` show a status at all, and appear among the warnings? Most warnings in Mali
   come from them (5 of 6), including the only `crisis`. If the usual level is unreliable without enough data, a
   status badge may raise false alarms; if it is reliable, the counts should probably include them.

Interim on the site (until answered): the counts are labelled "Status of the N series with a forecast"
(`series_with_forecast`); the warnings table keeps the series without a forecast but marks them "no forecast".

## Example
Export generated 2026-10-25T08:45:44, Mali:

| Source | normal | stress | alert | crisis |
|---|---|---|---|---|
| `countries.json` `status_counts` | 239 | 3 | 1 | 0 |
| `index/mali.json` (all series) | 352 | 19 | 5 | 1 |
| series files, `eligible: true` only | 239 | 3 | 1 | 0 |

Mali alert/crisis series, with `eligible`:
`mali-2516-58-retail-kg` (Wheat flour, Adjelhoc) crisis, false · `mali-250-64-retail-kg` (Rice (imported), Kidal)
alert, false · `mali-908-203-retail-kg` alert, false · `mali-2020-71-retail-kg` alert, false ·
`mali-2022-120-retail-kg` alert, false · `mali-1816-73-retail-kg` (Millet, Yorosso) alert, true.

Note for the pending conflict-area policy (contract §4.8): Kidal and Adjelhoc are in northern Mali. The site can hide
them through `config/hidden.json` as soon as the owner decides.

## Answer
1. **`countries.json` counting only series with a forecast is intended**; the contract now says so (§3): the counts
   equal the number of `eligible: true` rows per status in `index/<country>.json`.
2. **Series without a forecast get no status** (schema 1.1): `status` is `null` in `series/<id>.json` and in the
   indexes when `eligible` is false. Reason: these 183 series have 36-176 months of history (median 66) but too few
   usable months or too many gaps; their "usual level" comes from an unreliable seasonal fit, so a badge could be a
   false alarm (the only Mali `crisis` and 4 of the 5 `alert` were such series). Show them with "Not enough data for
   a forecast", outside the warnings and the counts. So the interim labels can go: home and country page now agree.
Kidal and Adjelhoc: noted for the conflict-area policy; that remains an owner decision.
