# Initial questions from the site agent

Status: answered (decisions marked "Owner decision" are recommendations until Sander confirms)
From: site agent, 2026-10-25 (relayed by Sander)

## Request
1. Static site generator: Astro (static) as the brief suggests, or 11ty?
2. Repo and GitHub: may I `git init` in `food-watch-web`? Create a GitHub repo, private or public, which account?
   Nothing is pushed until approved.
3. Vercel protection: the free plan protects preview deployments with Vercel login; production URLs stay public.
   Proposal: deploy only from a non-production branch until publication is approved.
4. The 95 % band in the fan chart: very light, or leave it out?
5. Real data locally: fetch `latest.tar.gz` once with the Databricks CLI profile `Fx-Workspace` into a git-ignored
   folder, to test the size budgets on all 1,091 pages? Otherwise build on the 3-series sample only.
6. Site name for titles and header: is "Food Price Watch" fine?

## Answer
1. **Astro, static output.** Agreed. No server adapter or server-side rendering is needed; ship zero JavaScript by
   default and add small islands only where the brief allows (filters, tooltips).
2. **`git init`: yes**, locally. **GitHub: owner decision.** Recommendation: a repository under the same account
   (`sgrout`), named `food-price-watch-web`, **private for now**. Reason: the contract's data flow commits the
   fetched export to the site repo; in a public repo that would publish all forecasts before the owner has approved
   publication. Make it public when the site is published (then the committed data is the intended, versioned
   public record). Until then, push only after the owner says so.
3. **Agreed.** No production deployment until publication is approved: set the production branch to one that
   does not receive pushes (or turn off automatic production deployments) and use preview deployments only, with
   Vercel Authentication on. Verify it by opening a preview URL in a private browser window (it must ask for a
   login). Keep the "Preview: not for use" banner and `noindex` anyway.
4. **Very light**, as recommended: label it "95 % range" in the legend, keep the 80 % range clearly dominant, and do
   not mention the 95 % numbers in headline text. The methods text already says the wide ranges are loose.
5. **Owner decision** (it uses the owner's login). Recommendation: yes, once, read-only, into a git-ignored folder,
   without printing or storing the token, e.g.
   `databricks fs cp dbfs:/Volumes/workspace/fpw_dev_gold/public_export/latest.tar.gz ./data-local/ --profile Fx-Workspace`.
   Never commit it while the repository could become public before publication. Building on the sample is fine for
   everything except the full-site budget check.
6. **Owner decision.** Caution: as far as the data side knows, "Food Price Watch" has been the name of a World Bank
   report series. The project must not look like a product of another organisation, so a clearly distinct name is
   safer. Options: keep the repository name in lower case as a plain label ("food-price-watch"), or choose a
   distinct name, e.g. "Market Price Outlook" or "Staple Price Signals". Use one constant in the string catalog so
   the name can change in one place.
