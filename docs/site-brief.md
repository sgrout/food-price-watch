# Site brief: the public food-price-watch site

Audience: the agent building the public site (separate repository, hosted on Vercel). Read this first, then
`export-contract.md` (the data), then `docs/README.md` (how we communicate). Owner and decision-maker: Sander.

## 1. What the site is for

Open, free, non-commercial early warning for staple food prices in Mali, Burkina Faso and Burundi (more countries
later). For each market and food it shows the price history, a forecast range for the next months, a chance of a
price spike, a short explanation in words, and an honest track record. It complements the official assessments of
WFP and FEWS NET; it never replaces them.

Users: analysts at small NGOs and local organisations, journalists, researchers. Many are **on phones, on slow or
expensive mobile data, sometimes with old devices**. English first; French follows (West and Central Africa).

## 2. Non-negotiables

1. **Fast and small** (section 4 has the budgets; CI must enforce them).
2. **Honest** (export contract §4): every forecast shows its range, the data date and a link to the track record;
   spike chance only where the data says so; numbers are never recomputed or rounded into a different meaning.
3. **Attribution** on every page and download: WFP via HDX, CC BY-IGO, plus the disclaimer and links to WFP HungerMap
   and FEWS NET.
4. **No personal data**: no cookies, no accounts, no third-party scripts, no ads, no tracking. Analytics only after the
   owner approves, and then only privacy-friendly and cookie-free.
5. **Nothing public without the owner's approval**: while `manifest.status` is `preview`, deploy only to protected
   preview environments, with a visible "Preview: not for use" banner and `noindex`.

## 3. Pages

| URL | Page | Content |
|---|---|---|
| `/` | Home | What the site is (2-3 sentences), the countries with status counts and data date, link to methods and track record |
| `/<country>/` | Country | Warnings first (series in `alert`/`crisis`, then `stress`), then all series grouped by food; each row: market, region (`admin1`), status (icon + label), next-month 80 % range, spike chance where shown. Plain HTML table/list; filtering by food and region may use a few lines of JS but must work without it |
| `/<country>/<series-id>/` | Market × food | Title (food, market, region, unit and currency), status badge, data date (`data_up_to` and forecast month), the `explanation`, the next-month and 3-month 80 % ranges, spike chance (if `show_spike_probability`), the fan chart, a table view of forecast and recent history, the country's track record for these horizons, flags legend, attribution. For `eligible: false`: history only and "Not enough data for a forecast" |
| `/track-record/` | Track record | Per horizon: how often the 80 % / 95 % range held, typical error, new-spike verdict (`better`/`no_better`/`worse` than the base rate) in words; per country; live results once present. Bad results are shown as clearly as good ones |
| `/methods/` | Methods | Render `site-content/methods.en.md` (do not rewrite its claims) |
| `/downloads/` | Downloads | Latest CSV, past CSVs (versioned), the README and the license; plain links |
| `/about/` | About | Render `site-content/about.en.md` |

Not now (keep the structure ready): French pages (`/fr/...`), a map of markets, RSS/email alerts per country, a
food-basket cost page. Do not add a heavy map library; a map, if approved later, is a small static SVG with dots.

## 4. Speed and size budgets (mobile, enforced in CI)

| Measure | Budget |
|---|---|
| Transfer per page on first visit (compressed, all requests) | **<= 100 KB**; a series page typically 30-60 KB |
| HTML per page (compressed) | <= 40 KB |
| CSS, whole site (compressed) | <= 15 KB, one file, cached |
| JavaScript per page (compressed) | <= 20 KB, and **every page works with JavaScript off** |
| Fonts | none: system font stack |
| Images | none except inline SVG (charts, icons) |
| Client-side data fetching | none on phone pages: render the data into the HTML at build time; never load `index.json` (410 KB) in the browser |
| Lighthouse, mobile (simulated slow 4G) | Performance >= 95, Accessibility 100, Best practices >= 95, SEO >= 90 |
| Core Web Vitals (lab) | LCP <= 2.0 s, CLS < 0.05, TBT < 100 ms |

Approach: a static site generator with zero JavaScript by default (Astro with static output is a good fit; 11ty is
fine too). No single-page-app shell, no React runtime on every page. Charts are inline SVG generated at build time
(see section 6). Keep the output vendor-neutral static files, so the site could move to Cloudflare or GitHub Pages.

## 5. Accessibility and language

- WCAG 2.2 AA. Semantic HTML (headings, lists, tables with headers), keyboard reachable, visible focus, readable at
  320 px width and at 200 % zoom, `lang` set per page.
- Status always as icon + label, never colour alone (normal ✓, stress ▲, alert ▲▲, crisis ■).
- Every chart has a text summary (the explanation) and a table view.
- All UI strings in one catalog per language (`en` now, `fr` later); the data's `explanation` comes per language key.
  Format numbers and month names per locale (English `1,250`; French `1 250`, decimal comma).
- Light and dark mode via `prefers-color-scheme`, both with sufficient contrast.

## 6. The fan chart (market × food page)

Same design as the project's private app, which has been checked in light and dark mode:
- One hue (blue `#2a78d6`; dark mode `#3987e5`): the observed price line and the forecast median (dotted, with
  markers). Bands in the same hue, translucent: 80 % range stronger, 95 % range lighter (or omitted, see the contract:
  its tails are loose). The fan starts at the last observed price.
- "Usual level for the season" (`usual_level`) as a dashed neutral grey line over the forecast months.
- `data_error` points as a neutral × marker, not on the line; `break` and `unconfirmed_jump` explained in the legend.
- Y axis from 0, labelled `<currency> per <unit>`; x axis months. A legend (several series); no dual axis.
- Default window: the last 5 years of history plus the forecast; the full history is in the table view / CSV.
- Hover/tap tooltips are an optional enhancement (tiny JS); the chart must be readable without them.

## 7. Data flow and resilience

As in the export contract §2: a scheduled GitHub Action fetches `latest.tar.gz`, verifies hashes and schemas,
commits the data, and Vercel deploys. If anything fails, nothing changes: the site keeps the last good data. The
build shows a "Data may be out of date" banner if `generated_at` is older than 14 days. Pages show `data_up_to`
prominently so staleness is visible to users.

Hiding: a config file (e.g. `hidden.json` with country ids and series ids) removes pages from the build without code
changes. The publication policy for conflict-affected areas is pending.

Secrets: `DATABRICKS_HOST` and `DATABRICKS_TOKEN` only as CI secrets; never in the repository, the build output, the
browser or `docs/`.

## 8. Quality checks in CI

Schema validation of the fetched data (`export/schema/`), the build, an internal link check, the size budgets
(section 4), Lighthouse CI on a few representative pages (home, a country, a series with and without forecast),
and an automated accessibility check (axe or pa11y). Also a check that every page contains the attribution string.

## 9. How to work with the owner and the data side

- Plan each step and present the choices that are the owner's before building; small, verifiable steps.
- Ask before anything outward-facing: a production domain, removing the preview protection or banner, allowing
  search indexing, enabling analytics.
- Need different or extra data? Write a request in `docs/site-requests/` (see `docs/README.md`); do not work around
  the contract or compute new numbers on the site side.
- Keep `docs/site-status.md` current (what exists, where it is deployed, open questions) and report honestly,
  including budgets that are missed.
