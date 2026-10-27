"""Countries in scope and their expected currencies (a different currency in the data stops the pipeline)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    slug: str  # as in the HDX dataset name: wfp-food-prices-for-<slug>
    iso3: str
    name: str
    currencies: tuple[str, ...]
    forecast: bool = True  # False: ingested and kept (our own publication record), but not forecast or exported


COUNTRIES = {
    c.slug: c
    for c in [
        Country("mali", "MLI", "Mali", ("XOF",)),
        Country("burkina-faso", "BFA", "Burkina Faso", ("XOF",)),
        Country("burundi", "BDI", "Burundi", ("BIF",)),
        Country("niger", "NER", "Niger", ("XOF",)),  # phase 6c (2026-10-27): public only after the owner's go
        # Chad: WFP publishes its prices 2-4 months late and irregularly (HDX activity: data to 2026-02 on 2026-05-24,
        # to 2026-05 on 2026-07-26, to 2026-06 on 2026-10-19), so with the origin - 2 rule its forecasts would come and
        # go. Owner decision 2026-10-27: ingest only; revisit with a per-country lag or when publication is regular.
        Country("chad", "TCD", "Chad", ("XAF",), forecast=False),
    ]
}
FORECAST_COUNTRIES = tuple(slug for slug, c in COUNTRIES.items() if c.forecast)

# Commodities that WFP re-specified under a new id, which we treat as one series: (country, old id) -> new id.
# Each entry needs evidence; quality.check_continuations fails the run if the price level at the switch differs
# by more than 25 %.
# - burundi 50 -> 829: "Beans" ends 2025-11, "Beans (haricot, yellow)" starts 2025-12 in 70 of the same 72 markets;
#   median price 2,649 -> 2,583 BIF/kg (-2.5 %).
CONTINUATIONS = {
    ("burundi", 50): 829,
}

# Staple foods (regex on the WFP commodity name, case-insensitive). Millet and cassava are staples in the pilot
# countries; "oil" means cooking oil, e.g. "Oil (vegetable)".
STAPLE_PATTERN = r"maize|rice|sorghum|millet|wheat|flour|beans|\boil\b|cassava|teff"
