# Côte d'Ivoire goes public (no schema change)

Status: done: Côte d'Ivoire is in the live exports (2026-11-27)
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
Site side, 2026-11-27: **ready. You can add Côte d'Ivoire to the live exports.**

**Tested** on both trial exports (items 2026-11-27T13:13:56, `model_version` 4; baskets 13:18:00). Hashes, sizes and
schemas pass (1.7 / basket-1.1); no schema or type change was needed.
- Build: 4,875 pages (live today: 4,813). Côte d'Ivoire has 30 pages per language: 26 market × food pages and
  4 basket pages, plus the country page. URLs and file names with `cote-d-ivoire` work; 93,723 internal links pass.
- Checks: budgets pass (heaviest page still /fr/mali/, 20.5 KB gzip), attribution, CSP and the consistency check
  (15,154 numbers). axe: 0 violations on 41 pages in light and dark mode, Côte d'Ivoire included. No horizontal
  scroll at phone width.
- **Small country:** the page reads well with 6 markets: status counts (20 normal), the empty "stopped reporting"
  and "far above the national price" sections ("no market…"), the four basket markets and the food tables.
- `countries.json` `note`: shown on the country page in both languages, with the track record link, as for Niger.
- `track_record.json`: `backtest.by_country.cote-d-ivoire` exists in both files and shows on the track record page
  and on the series and basket pages.
- Basket: denikassia rice + niébé reads well; the "Not included: cooking oil" line and your explanation show.
- French food names (`Riz importé (dénikassia)`, `Manioc (frais)`, `Huile de palme`, …) show; `missing_translations`
  is empty. (`Attiéké` does not appear in this export.)
- Apostrophe and circumflex: correct everywhere (titles, headings, captions, meta descriptions, JSON-LD).

**One site change:** the French strings put "au …" / "du …" before every country name, which is wrong for a feminine
name. They now give "**en** Côte d’Ivoire" (home description: "… au Burundi, en Côte d’Ivoire, au Mali, au Niger et
au Sénégal", in the manifest's order) and "les marchés **de la** Côte d’Ivoire". French pages also show the name with the typographic
apostrophe (`Côte d’Ivoire`) like other site strings; English pages and your texts keep it as given. Site commit
adec3d0, CI green.

**At the switch:** tell the owner. I will re-copy `site-content/about.{en,fr}.md`, run both update workflows and
check the Côte d'Ivoire pages live.

## Switch (data side, 2026-11-27)
Côte d'Ivoire is now in the live exports (`public_countries` = mali, burkina-faso, burundi, niger, senegal,
cote-d-ivoire). Items generated 2026-11-27T13:59:38 (`model_version` 4): 2,120 series (1,305 with a forecast; Côte
d'Ivoire 26, 20 with a forecast); baskets 14:11:05: 306 (Côte d'Ivoire 4). Same scope as the trial; hashes, sizes and
schemas pass on the downloaded files. Please re-copy `site-content/about.{en,fr}.md`, run both update workflows and
check the Côte d'Ivoire pages live. Thanks for the French prepositions ("en" / "de la").
