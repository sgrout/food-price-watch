# Keep foods that stopped reporting visible

Status: answered (data side, 2026-10-31): schema 1.7 and trial ready; waiting for the site to accept 1.7, then the data side switches
From: site side, 2026-10-31, on the owner's request

## Request
The owner asks to keep a food that stopped reporting on the site, labelled, instead of letting its page disappear.
This follows your answer in `2026-10-31-export-1-6.md`, which called it a separate decision (about 386 extra pages).

Today the export treats two similar cases differently:
- A **market** that stopped reporting stays visible, with "No price since <month>" (contract §4.9).
- A **food** that stopped in a market that still reports other foods leaves the export, and its page gives a 404.

The second case hides information the first was built to show. Since the switch to 1.6, Diapaga niebe has gone this
way, and Diapaga is one of the markets the market-signals request names as far above the national price. A food
vanishing from a market like that may itself be worth seeing. It also breaks links that people may have saved or shared.

**Proposed behaviour** (the rule and field names are yours to decide):
- Keep the series in the export with `eligible: false`, `status: null`, history only, as for silent markets.
- Give it a fact the site can show, for example `signals.food_silence {months, last_reported_month, reference_month}`
  next to `signals.silence`, and a ready-made `signals.text` (en, fr). The text should say that the market still
  reports other foods, and name other possible causes, such as the season or a change in what WFP monitors.
- Choose how long it stays. Silent markets are listed for 2-24 months, which seems a sensible starting point.
- These series must not count in `status_counts`, as for silent markets.

**Please also say:**
1. Whether a separate country list is wanted. My suggestion is no: label the series on its own page and in the
   per-food tables, and keep the "Markets that stopped reporting" section to whole markets.
2. What this means for baskets. Tougan and Diapaga leave on Monday because a basket needs all its foods in the item
   export. If the stopped foods return as history only, should those baskets stay out? Only the rule needs deciding;
   the site shows what the export has.
3. The schema version and rollout order. I suggest the same order as before: the site accepts the new schema first,
   then you switch.

**On the site side:** the label, the `signals.text` block, the chart and the per-food tables already exist for silent
markets, so this should be little work. About 386 extra pages is within what the build and the budgets handle now.

## Example
`burkina-faso-3367-120-retail-kg` (Diapaga, niebe): last price June 2026, the market still reports other foods. Live
until the 1.6 export, 404 now. With this change the page would return with "No price since June 2026" and its history.
The same goes for `burkina-faso-141-73`, `burundi-2440-76` and `niger-554-64` (all `-retail-kg`).

## Answer
(written by the data side, 2026-10-31)

**Yes, built as schema 1.7, not switched yet.** Trial in `fpw_dev_gold.public_export_next` (`latest.tar.gz`, generated
2026-10-31T15:23:15, not for the live site; its `baskets/` folder is not part of this trial): 1,704 series, 1,094 with a
forecast as before; 2.1 MB; hashes and schemas pass. It adds **311 pages, not about 386**, per language. Samples and
schemas are in `export/`; the contract has "Changes in 1.7" and §4.9.

**The rule:** as you proposed: `eligible: false`, `status: null`, history only, 2-24 months, at least 12 months of data, not
in `status_counts`. New: `signals.food_silence` (with `signals.text`, en and fr: show it as is) and index
`food_silent_months`. All 4 series of your example are back, each with `scope: market`.

**One addition you did not ask for: `food_silence.scope`.** Most stopped foods are not an event in that market, because
WFP changed its list around December 2025. So the text differs:

| `scope` | Meaning | Series | Example |
|---|---|---:|---|
| `country` | no market in the country reports it in this unit now | 188 | Burundi rice, Mali haricot beans |
| `market` | other markets still report it | 105 | Diapaga niebe |
| `other_unit` | this market now reports it in another unit (`other_unit`) | 23 | Mali oil, KG to L |

A short label should follow this too, because "No price since June 2026" alone suggests trouble on 211 pages where
none is shown. Suggestion: on `country` and `other_unit` use a neutral label, and on the per-food tables sort or group
these series below foods with a forecast. Your call how.

1. **Separate country list: no**, as you suggest. Label on the series page and in the per-food tables; the "Markets that
   stopped reporting" section stays whole markets. `silent_markets[]` does not change.
2. **Baskets: they stay out.** A basket needs a forecast for all its foods, and a stopped food has none. So Tougan and
   Diapaga leave on Monday as announced, and return if the food returns. The stopped foods are not used for this rule
   (the basket export reads the forecast summary, not the export), so nothing changes in the basket export or schema.
3. **Version and rollout: 1.7, additive, same order.** Accept 1.7 next to 1.6, build the label and say so here; only then
   the data side switches. Monday's run stays on 1.6.

**Please also re-copy** `site-content/methods.{en,fr}.md` (a new paragraph under "Markets that stopped reporting"), when
you build this. It describes behaviour that is live only after the switch, so copy it close to the switch.
