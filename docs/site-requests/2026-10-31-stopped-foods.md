# Keep foods that stopped reporting visible

Status: done (site, 2026-11-20): export 1.7 live
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

## Answer from the site side (2026-10-31)
**Schema 1.7 is accepted and the pages are on `main`; 1.6 keeps working and shows nothing new. You can switch.** Tell
us here (or the owner tells me): I then run the update by hand and copy `methods.*.md` at that moment, as you asked.

Tested with the trial export (generated 2026-10-31T15:23:15): hashes, sizes and schemas pass; 3,955 pages with the
current baskets; budgets (largest page 19.2 KB gzip), 76,019 links, attribution, CSP and 12,796 key numbers pass; axe 0
violations on the 29 usual pages and on 3 stopped-food pages (one per scope) before the final small fixes; no
horizontal scroll at phone width.

**Labels, using your `scope`:**
| `scope` | Label on page and in the per-food table | Look on the series page |
|---|---|---|
| `market` | ○ "No price since June 2026" / "Aucun prix depuis juin 2026" | grey signal block, as for a silent market |
| `country` | – "No longer reported in this country" / "Plus de prix publié dans ce pays" | plain paragraph, no block |
| `other_unit` | – "Now reported per L" / "Prix publié maintenant par L" | plain paragraph, no block |

`signals.text` follows as is, with a link to "Markets that stopped reporting".

**Per-food tables:** forecasts first, then silent markets and `market` scope, then "not enough data", then `country` and
`other_unit`. A food with no forecast in any market goes below the foods with one (in the jump list too). The scope
comes from the series files, since the index row has only `food_silent_months`.

**Also changed:**
- The "irregular reports" note and tag are not shown on stopped series: they talk about a forecast range these do not have.
- Chart caption: "Last 2 years" was wrong for a series that stopped, also for the silent markets live since 1.4: the
  window is the 2 years up to the last price, and the national median runs on after it. Those charts now say so.

## Switch (data side, 2026-11-20)
**Switch: done.** Export 1.7 generated 2026-11-20T07:49:06, status beta, four countries, 1,704 series (1,094 with a
forecast), checked on the downloaded `latest.tar.gz`: all 1,713 hashes and sizes match, all schemas pass.
`food_silence.scope`: 188 `country`, 105 `market`, 23 `other_unit` (316), the same as the trial. Please copy
`methods.{en,fr}.md` now and run your update by hand; say here when it is live.

Note: the scheduled runs of 9 and 16 November did not start (the Databricks scheduler did not trigger them; no
failure, no email). **Update, same day:** a full run made a new export, generated 2026-11-20T08:23:48: 1,712 series
(1,146 with a forecast), `data_up_to` 2026-10 (Burkina Faso 2026-09), `food_silence.scope` 190 `country`, 87
`market`, 24 `other_unit` (301); all 1,721 hashes and schemas pass. It carries **the first live track record**
(`live.by_horizon`: step 1, n 39, 80 % coverage 0.769). With no new spike among those 39, `base_rate_score` is 0 and
`new_spike_verdict` is `no_better` (this crashed the export before the fix; no contract change). Please fetch this
one.

## Live (site, 2026-11-20)
The update workflow fetched export 1.7 (generated 2026-11-20T07:49:06): 1,704 series, 1,094 with a forecast; all checks
passed. `methods.*.md` re-copied at the switch. Verified on staplesignals.org: Diapaga niebe is back with "No price
since June 2026", Goundam haricot beans with "No longer reported in this country", a French `other_unit` page with "Prix
publié maintenant par L", the new methods paragraph, and 3,950 URLs in the sitemap. Baskets unchanged (basket-1.1 of
2026-11-02).
