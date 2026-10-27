# About text: "no tracking" is no longer accurate (Vercel Web Analytics)

Status: accepted (owner decision 2026-10-26; about.*.md updated 2026-10-27)
From: site agent, 2026-10-25

## Request
The owner approved minimal analytics (site brief §2.4: "only after the owner approves, and then only
privacy-friendly and cookie-free"). The site now uses **Vercel Web Analytics**: no cookies, no personal data, no
cross-site tracking; it counts page views anonymously. `about.en.md` and `about.fr.md` still say "no tracking" /
"ni suivi", which is no longer accurate. Please update both texts (the site renders them, it does not rewrite them).

The site footer already says: "No cookies and no personal data; anonymous visit counts (Vercel Web Analytics)." /
"Pas de cookies ni de données personnelles ; comptage anonyme des visites (Vercel Web Analytics)."

## Example
`about.en.md`: "**No personal data.** The site uses no cookies and no accounts. It counts visits anonymously with
Vercel Web Analytics, which stores no personal data and does not follow visitors across sites."

`about.fr.md`: "**Aucune donnée personnelle.** Le site n'utilise ni cookies ni comptes. Il compte les visites de
façon anonyme avec Vercel Web Analytics, qui ne conserve aucune donnée personnelle et ne suit pas les visiteurs
d'un site à l'autre."

## Answer
Owner decision (2026-10-26, relayed by the site agent): the about texts use the same wording as the site footer.
The site already shows it (site repo `content/about.*.md`); please put the same sentence in
`docs/site-content/about.*.md`, so the next copy does not bring back "no tracking":

- en: "**No personal data.** No cookies, no accounts and no personal data; anonymous visit counts (Vercel Web
  Analytics)."
- fr: "**Aucune donnée personnelle.** Pas de cookies, pas de comptes ni de données personnelles ; comptage anonyme
  des visites (Vercel Web Analytics)." (narrow no-break space before ";")
