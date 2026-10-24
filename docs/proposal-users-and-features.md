# Proposal: who to build for, and what to add (for review)

Status: **idea for discussion, not approved.** Written 2026-10-24 from web research, for the coding agent to review.
Sander would like your honest opinion: what is sound, what is wrong or premature, what it would cost, and where it
fits in the phases. Do not start building any of it before he decides. Nothing here changes the Phase 2/3 work in
progress (calibration, leakage fixes) — that comes first.

## 1. Landscape: what already exists (and the gap)

| Who | What they publish | Gap for us |
|---|---|---|
| WFP (DataViz Economic Explorer, ALPS) | Point forecasts per market (ARIMA / seasonal Holt-Winters, chosen by RMSE) and ALPS alerts | Method note reports no accuracy/backtest figures; structural breaks not modelled per market; mainly for WFP's own programming |
| World Bank Real-Time Food Prices (RTFP) | 37 countries, ~3,100 markets, weekly; ML imputation of missing prices; open data | No forecasts. Could be a cross-check or extra input (license to verify) |
| FEWS NET | Hand-written country outlooks using national price systems (e.g. Burkina SIM/SONAGESS) | Paused reporting on several countries in 2026; not market-level forecasts |
| REACH joint market monitoring (Burkina "ICSM") | Monthly cost of the full Minimum Expenditure Basket (23 food + 26 non-food items), 17 markets, 6 NGOs, set up for the Cash Working Group | Current prices only, no forecast |

Our niche stays the same: **open, probabilistic, market-level forecasts with a published track record.**

## 2. Proposed primary user: cash programmes (Cash Working Groups)

- Cash and voucher assistance was ~21 % of humanitarian aid in 2025 (~US$7.3 bn).
- Transfer values are set from the cost of a **Minimum Expenditure Basket (MEB)**; inflation erodes them silently.
  Example: FEWS NET (July 2026) says inflation reduced refugee cash assistance in Burundi to **45–55 % of the MEB**.
- Cash Working Groups often update the MEB only every ~6 months (e.g. Yemen guidance: bi-annual).

**Idea:** a **food-basket cost index per market** (using each country's CWG basket composition and quantities),
with a 1–3 month probabilistic forecast and a plain statement such as: "the food basket in market X will likely
cost 8–15 % more by January; a transfer value set today would then cover about Y %."

Questions for you:
- Can a basket forecast be built from our per-commodity quantile forecasts? (Needs the joint distribution:
  commodity errors are correlated within a market — sum of quantiles ≠ quantile of the sum. Options: forecast the
  basket cost series directly, or simulate from correlated residuals.)
- Basket items not in WFP data (or with gaps): how to handle missing components honestly?
- Where can we get each country's official MEB composition (likely CWG documents on ReliefWeb Response / CaLP)?

## 3. Data gaps in crisis areas (Burkina Faso blockades)

- FEWS NET (Feb 2026): towns like Djibo, Arbinda, Sebba wait 6+ months for supplies (Djibo last resupplied June
  2025); local millet/sorghum rose 14–47 % in a month while national averages were *below* normal.
- **Idea A — "market silent" flag:** a market that stops reporting is itself a warning; show it instead of hiding it.
- **Idea B — local vs national gap:** price relative to the national median per commodity.
- **Backtest link:** check whether series drop out more often after a spike/onset. If so, our onset recall is
  optimistic (we only score observed targets). This is a validation question for Phase 2/3 regardless.

## 4. Feature candidates (ranked by value to users)

1. Food-basket cost index + forecast per market (section 2).
2. French pages and downloads first for Mali/Burkina (and Burundi); Kirundi later.
3. Low-bandwidth outputs: a monthly one-page bulletin (PDF/PNG that works in WhatsApp) + CSV. Confirm the channel
   with real users before building.
4. Terms of trade / purchasing power: livestock vs cereal (e.g. goat vs bag of millet), daily wage vs staple.
   FEWS NET uses these. Check what WFP data has (livestock in Mali; wages?).
5. Burundi drivers: parallel exchange rate and fuel. Our WFP exchange-rate series stops in 2024-04 → need another
   source (point-in-time and license checks first).
6. Later: anticipatory action. Mali has frameworks (OCHA food-insecurity activation 2023, ~US$7 M); triggers get
   peer-reviewed by the HDX Centre. Offer prices as a *supporting* indicator, never as an automatic trigger.
7. Cross-check with World Bank RTFP (do our nowcasts and their imputations agree?).

## 5. Outreach (Sander, not the agent)

- Cash Working Group coordinators in Bamako, Ouagadougou, Bujumbura (via CaLP / ReliefWeb Response). One question:
  "Would a 3-month food-basket cost forecast with a published track record help you set transfer values?"
- REACH / IMPACT: compare their market prices with ours; possible partner.
- HDX: publish forecasts as an HDX dataset + showcase; later ask the HDX Centre for a model peer review.

## 6. What I'd like from you (the agent)

1. Your opinion per section: agree / disagree / premature, with reasons.
2. Technical feasibility and rough effort of the basket forecast (section 2), and the right place in the phases.
3. Any risk to the honesty principles (e.g. a basket number looking more certain than its parts).
4. What would you change in Phase 3 now, if anything, so this stays cheap to add later
   (e.g. keep joint residuals per market, store basket compositions as data).

## Sources

- WFP, Food Price Forecasting and Alert for Price Spikes: https://docs.wfp.org/api/documents/WFP-0000155936/download
- World Bank, Real-Time Food Prices: https://microdata.worldbank.org/index.php/catalog/4483
- FEWS NET, Burundi Key Message Update, July 2026: https://fews.net/east-africa/burundi/key-message-update/july-2026
- FEWS NET, Burkina Faso Food Security Outlook, Feb 2026: https://fews.net/west-africa/burkina-faso/food-security-outlook/february-2026/print
- REACH, Burkina Faso ICSM factsheet, March 2024: https://repository.impact-initiatives.org/document/impact/a772545f/REACH_BFA_ICSM__Factsheet_mars_2024-1.pdf
- ALNAP, State of the Humanitarian System 2026, cash: https://alnap.org/help-library/resources/sohs-2026/chapter-2-what-works-and-at-what-cost/2-2-cash/
- CaLP, Yemen MEB/MPCA transfer value guidance: https://www.calpnetwork.org/?p=232119
- Anticipation Hub, Mali: https://www.anticipation-hub.org/global-overview/countries/mali
- HDX Centre, Burkina Faso drought AA trigger: https://centre.humdata.org/model-report-drought-anticipatory-action-trigger-in-burkina-faso/
