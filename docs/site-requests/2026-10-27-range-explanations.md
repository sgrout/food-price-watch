# Explain why the ranges are wide (owner request)

Status: open (for the site side to build)
From: data side, 2026-10-27, on the owner's request

## Request
The owner found the ranges hard to understand. Example: the basket in Diapaga (Burkina Faso), November 2026:
3,747-8,115 XOF per person per month. Such ranges are honest (in the 2023+ test the 80 % range held 77 % of the
time), but without an explanation a reader thinks the forecast is careless or useless. Three changes:

1. **A short note under every 80 % range**, on market × food pages and basket pages (en and fr): render
   `site-content/range-note.{en,fr}.md` as is, directly below the next-month / 3-month ranges (not only on the
   methods page: most readers never open it). Plain text, a link to the methods anchor; no JS, no tooltip needed.
   The anchors in the link assume your heading slugs (`#why-the-ranges-are-wide`,
   `#pourquoi-les-intervalles-sont-larges`); adjust the link to your slug rule if it differs, but keep the text.
2. **Methods page**: re-copy `site-content/methods.{en,fr}.md`. New: a "How to use it" paragraph under "How to read
   the range" and a new section "## Why the ranges are wide" / "## Pourquoi les intervalles sont larges".
3. **Explanations of markets whose last price is old** (data side, no site work): from the next item export
   (Monday 2026-11-02) and the basket export (regenerated today), the `explanation` gains one sentence when a
   market's last price is older than `data_up_to`, e.g. "No price has been published for this market since June
   2026: November 2026 is 5 months after the last known price, so the range is wider than usual." Today this applies
   to 11 food series and 6 baskets. No field or schema change (still 1.3 / basket-1.0); your consistency check is not
   affected (the sentence adds a month count, not a price).

Optional, if it fits the budgets: on the chart, show the gap between the last observed price and the first forecast
month visibly (it already is: no line between them); no extra element needed if the note is present.

## Example
`burkina-faso-3367-basket-ration_v1` (Diapaga): last complete basket cost June 2026, `data_up_to` 2026-08; its
explanation now contains the note above (basket wording: "No complete basket cost has been published for this
market since June 2026: November 2026 is 5 months after it, so the range is wider than usual.").

## Answer
(written by the site side)
