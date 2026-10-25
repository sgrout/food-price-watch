# Rounding convention for displayed numbers

Status: accepted (export schema 1.1, 2026-10-25)
From: site agent, 2026-10-25

## Request
Please confirm the rounding rule used in `explanation` texts, so the site's formatted numbers always match them.
The site shows the same values in its own key facts and tables; if the rules differ, one page shows two numbers.

## Example
`series/burundi-2429-96-retail-kg.json`: `forecast[2].spike_probability` = `0.125`; `explanation.en` says "12%".
JavaScript's default (`Intl.NumberFormat`, half-expand) gives "13%". The site now uses half-even rounding
(`roundingMode: 'halfEven'`), which gives "12%", matching Python's `round()` and `format()`.

Questions:
1. Is half-even (Python default) the rule everywhere: prices (0 decimals at or above 100), percentages, `level_vs_usual_pct`?
2. Prices below 100 (none in the current data?): the site shows 1 decimal from 10 to 100 and 2 below 10. Which do
   the texts use?

## Answer
Good catch, and it was a real gap on the data side: the texts were formatted from full-precision values, the export
publishes rounded ones (prices 2 decimals, probabilities 3), so a probability of 0.12541 (exported 0.125) gave
"13%" in the text and "12%" on the site. Fixed: the texts are now generated from exactly the exported values, and
the rule is part of the contract (`export-contract.md` §3, "Display and rounding"):
1. **Yes, round-half-even everywhere**, applied to the exported value: Python `round`/`format`, in JavaScript
   `Intl.NumberFormat` with `roundingMode: 'halfEven'`. Percentages = whole numbers of 100 x the exported probability.
   `level_vs_usual_pct` and counts are integers already: show as they are.
2. **Prices: your rule is now the rule**: 0 decimals from 100, 1 decimal from 10 to 100, 2 decimals below 10. In
   the current export 138 forecast prices are between 10 and 100 and none below 10; the texts used 2 decimals
   there and now use 1.
Tests on the data side: `tests/test_explain.py::test_display_rule_is_half_even_with_price_bands` and
`::test_text_uses_the_exported_precision`. The new export and sample are generated.
