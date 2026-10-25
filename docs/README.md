# docs/: how the data side and the site side communicate

This repository (food-price-watch) produces the data; a separate repository builds the public site on Vercel. The two
are built by different agents. They communicate only through files in this `docs/` folder, read and written via git.
The project owner (Sander) decides; neither agent publishes anything or changes the other side's code without him.

## Who owns which file

| File | Owner (writes) | Reader | Purpose |
|---|---|---|---|
| `site-brief.md` | data side | site agent | What the site must do and how: pages, speed and size budgets, accessibility, honesty rules, workflow |
| `export-contract.md` | data side | site agent | The data files: where, how to fetch, every field, rules (v1.0) |
| `site-content/*.md` | data side | site agent | Texts whose claims must stay accurate (methods, about); render them, do not rewrite them |
| `site-requests/*.md` | site agent | data side | Questions, requests for data changes, bug reports about the data |
| `site-status.md` | site agent | data side, owner | Short running status of the site: what exists, where it is deployed, open questions |
| everything else | data side | | Project documents (reviews, proposals) |

Machine-readable parts of the contract live outside `docs/`: `export/schema/` (JSON Schemas) and `export/sample/`
(real sample files).

## How to ask and answer

1. The site agent creates `site-requests/YYYY-MM-DD-<short-topic>.md` using the template in
   `site-requests/README.md` (status line `Status: open`).
2. The data side answers in the same file under `## Answer`, changes the status to `answered`, `accepted` (with the
   version/commit that delivers it) or `declined` (with the reason), and updates the contract if anything changed.
3. A change to the data contract is never made by the site side. If the site needs a new field, it asks.
4. Keep files short and factual; one topic per file; never put secrets (tokens, passwords) in `docs/`.
