# Site status

Owner of this file: the site agent (see `docs/README.md`). Keep it short and current.

Status: preview deployed on Vercel (protected) with the real export of 2026-10-25; CI green (2026-10-25)

- Repository: https://github.com/sgrout/food-price-watch-web (private). `main` = the site; `production` = a
  placeholder "Not published" page, used as Vercel's production branch until publication is approved.
- Deployments: preview of `main` at https://food-price-watch-web-git-main-sgrout.vercel.app/ (Vercel
  Authentication; verified: unauthenticated request redirects to the Vercel login). Production
  (food-price-watch-web.vercel.app) serves only the "Not published" placeholder, with `noindex`.
- Pages done (Astro 7, static): home, country, market × food (fan chart, forecast and history
  tables, country track record), track record, methods, about, downloads (CSV + README, hidden series removed), 404.
  Preview banner, `noindex`, stale-data banner (build time + tiny script), `config/hidden.json`.
- Budgets, measured on the full export of 2026-10-25 (local build, 1,100 pages; not committed): heaviest page
  /burundi/ 12.3 KB gzip (6.8 KB Brotli; budget 40 KB HTML, 100 KB page); series pages median 4.3 KB, max 6.0 KB;
  CSS 1.9 KB (15 KB); JS < 1 KB per page. 15,252 internal links OK; axe 0 violations on real pages (light, dark).
  Lighthouse mobile (sample build): performance 100, accessibility 100, best practices 100, SEO 63 (only
  `is-crawlable`, because of the intentional `noindex`).
- CI green on GitHub: build with hash + schema check, budgets, links, attribution, CSP, axe,
  Lighthouse; weekly data workflow (Mondays 09:00 UTC).
- Owner decisions: fan chart window = last 2 years + forecast (brief §6 said 5 years); full history in the table.
- Open questions / requests: `site-requests/2026-10-25-rounding-convention.md` (open),
  `site-requests/2026-10-25-status-counts-and-ineligible-status.md` (open).
- Data workflow: first run 2026-10-25 succeeded (fetch, sha256 + size + schema check, build, checks, commit);
  weekly Mondays 09:00 UTC. Bot commits deploy on Vercel. `DATABRICKS_TOKEN` expires 2027-01-24: renew before then.
