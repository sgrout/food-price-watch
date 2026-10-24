# External review: Phase 2 backtest code (2026-10-24)

Reviewer: Sander's assistant (Claude, separate chat). Read-only review of the code, tests, README and CLAUDE.md as
they were at about 16:20 local time on 2026-10-24 (Phase 2, before the Phase 3 merge). **No result tables were
checked** (no access to the workspace). Rechecked at 17:35: issue 1 still applies to `monthly_panel`, which the
Phase 3 notebook `04_backtest.py` also uses. The Phase 3 code (`calibrate.py`, `features.py`, `ml.py`,
`distribution.py`) has **not** been reviewed.

Overall: careful work. Lag handling, refit per origin, `common_rows`, onset vs persistence, standard errors over
origins, and the "change the future, past unchanged" test are all right. The issues below are real but fixable.
Please verify each one yourself before acting on it; this is a review, not a fact.

## 1. Look-ahead through the suspect flags (likely; makes the backtest look better than live)

`quality.flag_suspects` marks `spike_revert` using the *next* month (jump in, full reversal out). It runs once in
silver on the full history. `panel.monthly_panel` then drops `is_suspect` rows before `walk_forward` sees them.
Two effects:

- **History:** if the last usable month at origin O (month O - 2) is a blip that only reverts at O - 1 or later, the
  backtest has already removed it. A live run at O would see it as `unconfirmed_jump` (kept, not suspect) and
  forecast from it, possibly from a level off by x2-3.
- **Targets:** targets later classified as `spike_revert` are never scored, while live forecasts will be.

`test_forecasts_do_not_change_when_the_future_changes` does not catch this because the simulated panel bypasses
`flag_suspects`.

Suggested fix: decide suspect status as of the origin (a row is suspect at O only if the month that reverts it is
<= O - LAG), e.g. keep flagged rows in the panel with the date of the confirming month and filter per origin.
Suggested test: a series with a blip at O - 2 that reverts at O - 1; assert the forecast at O uses the blip.
Expected impact: small on the published means (the big Mali Aug 2017 episode is in dev), but it matters for the
live track record and for any series with a blip in its latest month. Count how many origin/series cases are
affected to size it.

## 2. Revisions and late backfills are not simulated (unavoidable for history; document it)

The panel uses current `wfp_prices`, not `silver.as_of`. "Usable from M + 2" models the delay but not values that
were corrected or months filled in later. History cannot be reconstructed (snapshots start 2026-10-24). Say so on
the methods page; after a few months of weekly snapshots, measure first-seen vs current values. The WFP email asks
about this.

## 3. Backtest population vs published population

The backtest scored 1,417 series; the eligibility rule gives 909. The track record shown next to a forecast should
come from series that would have been eligible *at that origin* (eligibility computed from data <= O - 2).

## 4. Spike definition partly measures persistent inflation

Base rate 50 % in 2020-22. A lasting level shift (Mali 2022 sanctions, Burundi devaluation) stays a "spike" for
years against a 10-year linear trend, and sigma biased ~10 % low inflates z. Check the base rate per country;
consider a shorter or robust/local trend, or deflated prices, so "spike" means what users expect. Onset metrics
already protect the evaluation; this is mostly about what users will read.

## 5. Missing targets may not be missing at random

Only observed targets are scored. Markets tend to stop reporting in crises (blockaded towns). Check whether series
drop out more after a spike/onset. (The Phase 3 docs mention dropout and blockade-town checks; not reviewed.)

## 6. Calibration

Calibrate only on errors from past origins (rolling, per step). The 2020+ volatility regime matters more than the
method. The 2023+ holdout is spent; the live track record is the only fully clean test, so start storing live
forecasts early. (The Phase 3 "recalibration with past PITs" sounds like the right approach; not reviewed.)

## ALPS reference

WFP, *Technical Guidance Note: Calculation and Use of the Alert for Price Spikes (ALPS) Indicator*, April 2014:
https://docs.wfp.org/stellent/groups/public/documents/manual_guide_proced/wfp264186.pdf
(landing page: https://vamresources.manuals.wfp.org/docs/alps-calculation-and-use-of-the-alert-for-price-spikes-indicator)

Summary as read by the reviewer (check against the PDF): OLS of the **price level** (not log) on a linear trend plus
12 monthly dummies, no constant, over the market's **whole available series** (minimum ~36 months); ALPS = positive
difference between observed and fitted price divided by the residual standard deviation; normal < 0.25 <= stress
< 1 <= alert < 2 <= crisis. Note on "only positive deviations": for our spike rule (z >= 1) this makes no difference;
it only matters for how below-normal prices are classified (ALPS calls them normal). Fitting on the whole series is
fine for WFP's monitoring but would be look-ahead in a backtest, so our origin-only fit is a deliberate difference.
