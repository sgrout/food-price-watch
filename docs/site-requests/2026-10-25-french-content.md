# French content

Status: open
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
(written by the data side)
