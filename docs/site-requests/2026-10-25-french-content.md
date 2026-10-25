# French content

Status: accepted (export schema 1.2, 2026-10-25)
From: site agent, 2026-10-25

## Request
The owner wants the site in English and French now (`/fr/...`, brief §5). The site translates its own interface.
Content that comes from the data side, and whose claims must stay accurate, is needed in French from the data side:

1. `explanation.fr` in `series/<id>.json` (the contract already plans per-language keys). Number format per the
   French locale: `1 250` (narrow no-break space as thousands separator), decimal comma, `12 %`.
2. French food names: `commodity.name_fr` in `series/<id>.json` and `commodity_fr` in the indexes (or a separate
   `commodities.json` with `{id, name: {en, fr}}`), so food names are not translated ad hoc on the site.
3. `site-content/methods.fr.md` and `site-content/about.fr.md`.
4. Optional: French `attribution` / `disclaimer` strings, and a French `downloads/README.txt` (or a bilingual one).

Until these exist, French pages show English for that content (marked with `lang="en"` for screen readers).

## Example
```json
"commodity": {"id": 73, "name": "Millet", "name_fr": "Mil", "group": "millet"},
"explanation": {"en": "...", "fr": "En août 2026, le prix était 29 % au-dessus du niveau habituel..."}
```

## Answer
All four delivered in export 1.2 (contract §3):
1. `explanation.fr` in every series with a forecast, from the same facts as `en`; French typography: narrow no-break
   space (U+202F) as thousands separator and before `%` and `:`, decimal comma (`1 250`, `94,6`, `12 %`). WFP's
   French ALPS terms: normal, stress, alerte, crise; a spike is "une flambée des prix".
2. `commodity.name_fr` in series files and `commodity_fr` in the indexes (15 WFP names: Mil, Sorgho, Maïs, Niébé,
   Riz (importé), ...). A future WFP name without translation falls back to English and is listed in
   `manifest.missing_translations`.
3. `site-content/methods.fr.md` and `site-content/about.fr.md` (same claims as the English versions).
4. `manifest.attribution_fr` and `manifest.disclaimer_fr`; `downloads/README.txt` is bilingual. The JSON
   `attribution` fields stay English (the license attribution); show `attribution_fr` on French pages.
The owner decided the French texts are not reviewed by a native speaker; report any wording problem as a request.

**Action for the site before Monday 09:00 UTC:** copy `export/schema/` (schema_version `1.2`) and `export/sample/`
(now 4 series, incl. an irregular market) into the site repository; the live export is already 1.2.
