# Côte d'Ivoire goes public (no schema change)

Status: open
From: data side, 2026-11-27, on the owner's go

## Request
The owner gave the go for **Côte d'Ivoire** (`cote-d-ivoire`, currency XOF; the name is the same in French, so the
site's own French country names need no entry, but check the apostrophe and the circumflex render everywhere).

**No schema change:** items stay 1.7 and baskets basket-1.1.

**Rollout (same order as Senegal):**
1. Test with the **trial exports** in the volume `fpw_dev_gold.public_export_next` (`latest.tar.gz` and
   `baskets/latest.tar.gz`; not for the live site). Items generated 2026-11-27T13:13:56 (`model_version` 4): 2,120
   series (1,305 with a forecast), six countries; Côte d'Ivoire 26 series in 6 markets, 20 with a forecast. Baskets
   generated 13:18:00: 306 baskets (263 with a forecast); Côte d'Ivoire 4 (all with a forecast). Hashes, sizes and
   schemas pass on the downloaded files (2,438 files checked). 2.5 MB + 0.3 MB.
2. Tell us here (Answer) when the site handles it. **Only then the data side adds Côte d'Ivoire to the live exports**
   (`public_countries`); until then the live exports keep five countries.
3. At the switch, re-copy `site-content/about.{en,fr}.md` (now "… Senegal and Côte d'Ivoire" / "… le Sénégal et la
   Côte d'Ivoire").

**Please check:**
- **A small country:** the country page with only 6 markets, all in the north and west (Savanes, Man; none in
  Abidjan), 26 series pages and 4 basket pages per language. The map, lists and status counts should still read
  well with so few markets; budgets and link checks.
- `countries.json`: Côte d'Ivoire has a fixed `note` (like Niger) saying that forecasts cover few markets and the
  track record rests on few cases; please show it on the country page as for Niger.
- `track_record.json` `backtest.by_country.cote-d-ivoire` (items and baskets) exists. Its numbers rest on few cases
  (about 450 holdout cases per step); nothing to build, just check it reads fine.
- The basket is denikassia rice + niebe (no oil: the oil series are too short); its `note` in the basket files says
  so, like Senegal's.
- New French food names (`Riz importé (dénikassia)`, `Attiéké (semoule de manioc)`, `Manioc (frais)`) if they
  appear; `missing_translations` is empty.
- The slug contains hyphens only (`cote-d-ivoire`): check URLs and file names (`series/cote-d-ivoire-*.json`).

**Also in the live exports (five countries, no change needed):** since 2026-11-26 they come from models retrained on
six countries (`model_version` 4); the weekly fetch on Monday picks that up as usual.

## Example
Any `series/cote-d-ivoire-*.json` and `basket/cote-d-ivoire-*-basket-ration_v1.json` in the trial exports.

Côte d'Ivoire's backtest (2023 onwards, all cases), for context: the 80 % range held 81.2 % next month and 77.9 %
three months ahead; typical errors 8.5 % and 10.5 %.

## Answer
