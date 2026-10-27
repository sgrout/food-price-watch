# Site status

Owner of this file: the site agent (see `docs/README.md`). Keep it short and current.

Status: PUBLIC BETA at https://staplesignals.org since 2026-10-25 (export 1.4 since 2026-10-27, status beta); CI green

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
- Contract 1.1 adopted (schemas copied, `status: null` handled: no badge, not in warnings or counts).
- Consistency check on every build: each key number on a series page must appear in its explanation. Export
  2026-10-25T12:51: 4,539 of 4,540 match; the one difference is in
  `site-requests/2026-10-25-half-even-on-decimal-values.md` (open). Report-only: it does not block data updates.
- Requests answered: rounding convention, status counts (both done on the site side).
- French (2026-10-25): all pages also under `/fr/` (2,199 pages). UI translated on the site side (native review
  welcome); explanations, food names, methods/about, attribution/disclaimer still English (marked `lang="en"`):
  see `site-requests/2026-10-25-french-content.md` (open).
- SEO groundwork: canonical, hreflang, Open Graph, sitemap.xml, schema.org Dataset; robots.txt follows
  `manifest.status`. Still `noindex` (meta + `X-Robots-Tag`) until the owner approves publication. Canonical URLs use
  https://food-price-watch-web.vercel.app until a production domain is chosen (`SITE_URL`).
- Conflict areas: shown (owner decision).
- Export 1.2 live on the site (generated 2026-10-25T14:11:41, fetched by the data workflow): French explanations,
  food names, attribution/disclaimer, methods/about; irregular-reporting note (wording from the request answer, numbers
  from `by_reporting`), marker in the country lists, track record by reporting. Schemas kept per version
  (`schema/1.1`, `schema/1.2`); the site accepts both.
- Public beta (go 2026-10-25): site ready. Name Staple Signals; schemas 1.3 copied (from your working tree, to
  re-sync when committed); `status: beta` shows the §4.6 banner (en/fr) linked to the track record; unknown status =
  preview; French pages note "Traduction non revue"; feedback link to the data repo's GitHub issues. Tested on a
  synthetic 1.3 beta export: all checks pass, axe 0, Lighthouse 100/100/96/SEO 100.
- **Search indexing: the owner asked for it now** (overrides the soft-launch default in
  `go-public-beta.md` step 4). Indexing follows `manifest.status`: preview = `noindex` + robots disallow;
  beta/published = indexable, robots.txt with sitemap. Canonical: https://staplesignals.org.
- Domain: staplesignals.org on Vercel production (HTTPS OK, www → apex 308). Production serves branch `main`.
- Live check 2026-10-25 (production = branch `main`): en/fr pages 200 with the beta banner, robots.txt allows +
  sitemap, no `noindex`, HTTPS + HSTS, 404 page, analytics script served. Lighthouse on the live site (mobile):
  100/100/100/100, LCP 0.8-0.9 s, TBT 0, CLS 0, 9-18 KB transferred per page.
- **Open for the data side:** `site-requests/2026-10-25-about-text-analytics.md` (about texts still say "no tracking"
  while analytics is on); your 1.3 changes are still uncommitted in the data repo.
- Food baskets (2026-10-27, `site-requests/2026-10-27-basket-pages.md`, accepted; answers applied): 211 basket pages
  per language (basket export 2026-10-27T14:47), country sections, links from item pages, track record section.
  Separate workflow `update-baskets.yml` (Mon 09:30 UTC). Charts (items and baskets) start the fan at
  `last_observed_month`; prices published after `data_up_to` are drawn on the observed line, with a note. Methods
  links use the new `##` anchors. 2,619 pages; largest 16.4 KB gzip; 10,510 key numbers match their texts; axe 0;
  every basket market has item pages. Weekly item update of 2026-10-26 ran automatically.
- Range explanations (2026-10-27, accepted): "Why so wide?" note under every 80 % range (item and basket pages,
  en/fr), methods sections re-copied; basket export 2026-10-27T15:13 live with the old-price sentence (6 baskets).
- Market signals (2026-10-27, accepted): schema 1.4 accepted next to 1.3 (live); signal block, national median line,
  silent series, and the two country sections built and live, shown once the export is 1.4. Tested with the trial
  export: 2,803 pages, all checks pass, axe 0. Export 1.4 of 2026-10-27T17:23 live and verified (Mali 15 and Burkina Faso 1 silent markets; 29 series far above).
- Analytics (owner approved 2026-10-25): Vercel Web Analytics, cookie-free, no personal data; one cached loader
  (1.4 KB gzip) plus Vercel's script. Footer states it; `about.*.md` still says "no tracking":
  `site-requests/2026-10-25-about-text-analytics.md` (open).
- Consistency: all 9,080 key numbers on English and French series pages match their explanations (0 differences).
- Data workflow: first run 2026-10-25 succeeded (fetch, sha256 + size + schema check, build, checks, commit);
  weekly Mondays 09:00 UTC. Bot commits deploy on Vercel. `DATABRICKS_TOKEN` expires 2027-01-24: renew before then.
