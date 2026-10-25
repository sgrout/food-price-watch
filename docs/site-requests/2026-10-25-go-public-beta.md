# Go: public beta at staplesignals.org

Status: answered (owner's go, 2026-10-25)
From: data side, relaying the owner

## Request
(No request: the owner's decision, with the steps for the site.)

## Answer
The owner gave the **go for a public beta**. From now on the export has `manifest.status = "beta"` (schema 1.3).
Contract §4.6 has the banner texts (en/fr) and the rule for unknown statuses.

Steps for the site (report progress in `site-status.md`):
1. Copy `export/schema/` (1.3) and `export/sample/` into the site repository; handle `status: "beta"`.
2. Beta banner on every page (contract §4.6), linked to `/track-record/`.
3. Connect **staplesignals.org** to the Vercel project and make production serve the site (production branch,
   deployment protection off for production only). Check the Vercel plan terms for this use (the owner said he
   will upgrade to a paid plan if needed).
4. Launch defaults (the owner may change them): keep `noindex` and `robots.txt` disallow for now (a soft launch:
   the owner shares the link himself); French pages live with a short note "Traduction non revue / translation
   not reviewed"; a feedback link to https://github.com/sgrout/food-price-watch/issues (no personal data collected).
5. Before switching: run the full checks on the production build (budgets, links, attribution, axe, Lighthouse)
   and verify the live domain (HTTPS, banner, attribution, both languages) once it is up.
6. Ask the owner before anything further that is outward-facing (search indexing, announcements, analytics).

Beta exit criterion (fixed now, before any live result): live 80 % coverage of the published forecasts between 70 %
and 90 % after at least 6 matured forecast months, and the owner agrees. Then the export moves to `published`.
