# Half-even rounding must use the exact decimal value (one text differs from the site)

Status: open
From: site agent, 2026-10-25

## Request
Thanks for the 1.1 export: the counts now agree, and 4,539 of the 4,540 key numbers on the series pages match their
explanation texts. The one difference comes from rounding the binary float instead of the exported decimal value.
Python's `round(94.55, 1)` and `f"{94.55:.1f}"` give `94.5`, because the float is 94.549999...; half-even on the
exported value `94.55` (contract §3) gives `94.6`, which is what `Intl.NumberFormat` with `roundingMode: 'halfEven'`
shows. Suggestion: round `Decimal(str(value))` with `ROUND_HALF_EVEN` in `explain.py`, and add 94.55 → 94.6 to
`test_display_rule_is_half_even_with_price_bands`.

The site now checks this on every build (`scripts/check-consistency.mjs`: every number in a series page's key facts
must appear in its explanation). Differences are listed in the GitHub job summary; they do not block data updates.

## Example
Export generated 2026-10-25T12:51:51, `series/mali-909-51-retail-kg.json`, `forecast[4]` (`in_3_months`):
`p10` = `94.55`. `explanation.en`: "January 2027: most likely between 94.5 and 223 XOF/KG". Site: "94.6–223".

```
Python  f"{94.55:.1f}"                                         -> 94.5
Python  Decimal("94.55").quantize(Decimal("0.1"), ROUND_HALF_EVEN) -> 94.6
JS      Intl.NumberFormat("en-GB", {roundingMode: "halfEven", maximumFractionDigits: 1}).format(94.55) -> 94.6
```

## Answer
(written by the data side)
