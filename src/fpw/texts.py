"""User-facing text templates (string catalog): English and French. Add a language by adding the same keys.

Templates only take numbers from `fpw.explain` facts: no number is ever written by hand or by an LLM. French uses
WFP's French ALPS terms (normal, stress, alerte, crise) and French typography: a narrow no-break space (U+202F) as
thousands separator and before %, :, decimal comma.
"""

NNBSP = " "  # narrow no-break space (French thousands separator, before % and :)

# Public name of the site (owner decision 2026-10-25, domain staplesignals.org). Code, repositories and tables keep
# the internal name food-price-watch.
SITE_NAME = "Staple Signals"
SITE_URL = "https://staplesignals.org"

LANGUAGES = ("en", "fr")

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"],
}

# Number format per language: thousands separator, decimal mark.
NUMBER_FORMAT = {"en": (",", "."), "fr": (NNBSP, ",")}

# "in <country>" and the commodity group as used in a sentence.
IN_COUNTRY = {
    "en": {"mali": "in Mali", "burkina-faso": "in Burkina Faso", "burundi": "in Burundi"},
    "fr": {"mali": "au Mali", "burkina-faso": "au Burkina Faso", "burundi": "au Burundi"},
}
GROUPS = {
    "en": {"beans": "beans", "cassava": "cassava", "maize": "maize", "millet": "millet", "oil": "cooking oil",
           "rice": "rice", "sorghum": "sorghum", "wheat": "wheat", "flour": "flour", "other": "this food"},
    "fr": {"beans": "les haricots", "cassava": "le manioc", "maize": "le maïs", "millet": "le mil",
           "oil": "l'huile", "rice": "le riz", "sorghum": "le sorgho", "wheat": "le blé", "flour": "la farine",
           "other": "ce produit"},
}

# French names of WFP commodities (English WFP name -> French). A name missing here falls back to English and is
# listed in the export manifest (`missing_translations`), so it is noticed and added.
COMMODITY_FR = {
    "Beans (haricot, yellow)": "Haricots (jaunes)",
    "Beans (niebe)": "Niébé",
    "Cassava flour": "Farine de manioc",
    "Maize": "Maïs",
    "Maize (white)": "Maïs (blanc)",
    "Maize flour": "Farine de maïs",
    "Millet": "Mil",
    "Oil (palm)": "Huile de palme",
    "Oil (vegetable)": "Huile végétale",
    "Rice (imported)": "Riz (importé)",
    "Rice (local)": "Riz (local)",
    "Rice (paddy)": "Riz (paddy)",
    "Sorghum": "Sorgho",
    "Sorghum (white)": "Sorgho (blanc)",
    "Wheat flour": "Farine de blé",
}

TEXTS = {
    "en": {
        "status_normal": "normal", "status_stress": "stress", "status_alert": "alert", "status_crisis": "crisis",
        "level_above": "In {month} the price was {pct}% above the usual level for that time of year ({status}).",
        "level_below": "In {month} the price was {pct}% below the usual level for that time of year ({status}).",
        "level_at": "In {month} the price was at the usual level for that time of year ({status}).",
        "trend_up": "It rose {pct}% over the 3 months before.",
        "trend_down": "It fell {pct}% over the 3 months before.",
        "trend_flat": "It was about stable over the 3 months before.",
        "market_up": "For {group}, across {n} markets {in_country}, the median price rose {pct}% over those 3 months.",
        "market_down": "For {group}, across {n} markets {in_country}, the median price fell {pct}% over those 3 months.",
        "market_flat": "For {group}, across {n} markets {in_country}, the median price was about stable.",
        "forecast": "{Month}: most likely between {lo} and {hi} {currency}/{unit} (8 in 10 chance).",
        "spike": "Chance of a spike in {month} (price well above the usual level for the season): {p}%.",
        "caveat": "Warnings of new spikes have no proven skill yet (track record 2023-2026).",
        "stale": "No price has been published for this market since {month}: {next} is {k} months after the last "
                 "known price, so the range is wider than usual.",
    },
    "fr": {
        "status_normal": "normal", "status_stress": "stress", "status_alert": "alerte", "status_crisis": "crise",
        "level_above": "En {month}, le prix était {pct} % au-dessus du niveau habituel pour cette période de "
                       "l'année ({status}).",
        "level_below": "En {month}, le prix était {pct} % en dessous du niveau habituel pour cette période de "
                       "l'année ({status}).",
        "level_at": "En {month}, le prix était au niveau habituel pour cette période de l'année ({status}).",
        "trend_up": "Il avait augmenté de {pct} % au cours des 3 mois précédents.",
        "trend_down": "Il avait baissé de {pct} % au cours des 3 mois précédents.",
        "trend_flat": "Il était à peu près stable au cours des 3 mois précédents.",
        "market_up": "Pour {group}, sur {n} marchés {in_country}, le prix médian a augmenté de {pct} % sur ces "
                     "3 mois.",
        "market_down": "Pour {group}, sur {n} marchés {in_country}, le prix médian a baissé de {pct} % sur ces "
                       "3 mois.",
        "market_flat": "Pour {group}, sur {n} marchés {in_country}, le prix médian est resté à peu près stable.",
        "forecast": "{Month} : probablement entre {lo} et {hi} {currency}/{unit} (8 chances sur 10).",
        "spike": "Probabilité d'une flambée des prix en {month} (prix nettement au-dessus du niveau habituel pour "
                 "la saison) : {p} %.",
        "caveat": "Les alertes de nouvelles flambées des prix n'ont pas encore fait leurs preuves (historique "
                  "2023-2026).",
        "stale": "Aucun prix n'a été publié pour ce marché depuis {month} : {next} se situe {k} mois après le "
                 "dernier prix connu, l'intervalle est donc plus large que d'habitude.",
    },
}

ATTRIBUTION = {
    "en": "Source: World Food Programme (WFP), food prices via the Humanitarian Data Exchange (HDX), CC BY-IGO.",
    "fr": "Source : Programme alimentaire mondial (PAM), prix des denrées alimentaires via le Humanitarian Data "
          "Exchange (HDX), CC BY-IGO.",
}
DISCLAIMER = {
    "en": "Forecasts by Staple Signals, not an official WFP or FEWS NET assessment. "
          "Official assessments: https://hungermap.wfp.org and https://fews.net",
    "fr": "Prévisions de Staple Signals, pas une évaluation officielle du PAM ni de FEWS NET. "
          "Évaluations officielles : https://hungermap.wfp.org et https://fews.net",
}
