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
    "en": {"mali": "in Mali", "burkina-faso": "in Burkina Faso", "burundi": "in Burundi", "niger": "in Niger",
           "chad": "in Chad"},
    "fr": {"mali": "au Mali", "burkina-faso": "au Burkina Faso", "burundi": "au Burundi", "niger": "au Niger",
           "chad": "au Tchad"},
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
    "Beans (haricot)": "Haricots",
    "Beans (haricot, yellow)": "Haricots (jaunes)",
    "Beans (niebe)": "Niébé",
    "Beans (niebe, red)": "Niébé (rouge)",
    "Cassava": "Manioc",
    "Cassava (cossette)": "Cossettes de manioc",
    "Cassava flour": "Farine de manioc",
    "Maize": "Maïs",
    "Maize (white)": "Maïs (blanc)",
    "Maize flour": "Farine de maïs",
    "Millet": "Mil",
    "Oil (groundnut)": "Huile d'arachide",
    "Oil (palm)": "Huile de palme",
    "Oil (vegetable)": "Huile végétale",
    "Rice (imported)": "Riz (importé)",
    "Rice (local)": "Riz (local)",
    "Rice (paddy)": "Riz (paddy)",
    "Sorghum": "Sorgho",
    "Sorghum (berbere)": "Sorgho (berbéré)",
    "Sorghum (red)": "Sorgho (rouge)",
    "Sorghum (white)": "Sorgho (blanc)",
    "Wheat": "Blé",
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

# A fixed note per country about its track record (no numbers: those come from track_record.json); null if none.
COUNTRY_NOTES = {
    "niger": {
        "en": "Niger was added in October 2026. In its backtest the ranges were too narrow during the 2024-2025 shocks "
              "(after the July 2023 coup, with the border to Benin closed, and the 2024 floods): prices then fell "
              "outside them much more often than claimed. See the track record.",
        "fr": "Le Niger a été ajouté en octobre 2026. Dans les tests sur le passé, les intervalles étaient trop étroits "
              "pendant les chocs de 2024-2025 (après le coup d'État de juillet 2023, avec la frontière avec le Bénin "
              "fermée, et les inondations de 2024) : les prix en sont alors sortis bien plus souvent qu'annoncé. "
              "Voir la page sur la fiabilité des prévisions.",
    },
}

SIGNAL_TEXTS = {  # fpw.signals.describe_signals; numbers only from facts
    "en": {
        "gap_above": "In {month} the price here was {pct}% above the national median of {n} markets",
        "gap_below": "In {month} the price here was {pct}% below the national median of {n} markets",
        "gap_at": "In {month} the price here was about the same as the national median of {n} markets",
        "usual_above": " (usually {pct}% above)", "usual_below": " (usually {pct}% below)",
        "usual_at": " (usually about the same)",
        "far": "That is far above its usual distance: prices that separate from the rest of the country can point to "
               "a cut-off area, but also to a data error.",
        "silent": "No price has been published for this market since {month}, while most markets {in_country} "
                  "reported up to {ref}. Missing data can be an early sign of trouble, or have other causes, such as "
                  "a pause in monitoring.",
        "food_silent_market": "No price has been published for this food in this market since {month}, while the "
                              "market still reports other foods and other markets {in_country} still report this one. "
                              "This can have ordinary causes, such as the season or a change in what WFP monitors "
                              "here, but the food may also have become hard to find.",
        "food_silent_country": "No price has been published for this food in this market since {month}, and no market "
                               "{in_country} reports it now. This points to a change in what WFP monitors, not to a "
                               "problem in this market.",
        "food_silent_other_unit": "No price per {unit} has been published for this food in this market since {month}: "
                                  "WFP now reports it here per {other_unit}.",
    },
    "fr": {
        "gap_above": "En {month}, le prix ici était {pct} % au-dessus de la médiane nationale de {n} marchés",
        "gap_below": "En {month}, le prix ici était {pct} % en dessous de la médiane nationale de {n} marchés",
        "gap_at": "En {month}, le prix ici était à peu près égal à la médiane nationale de {n} marchés",
        "usual_above": " (d'habitude {pct} % au-dessus)", "usual_below": " (d'habitude {pct} % en dessous)",
        "usual_at": " (d'habitude à peu près égal)",
        "far": "C'est bien au-dessus de son écart habituel : des prix qui s'écartent du reste du pays peuvent "
               "signaler une zone coupée du reste, mais aussi une erreur de données.",
        "silent": "Aucun prix n'a été publié pour ce marché depuis {month}, alors que la plupart des marchés "
                  "{in_country} ont publié jusqu'en {ref}. L'absence de données peut être un premier signe de "
                  "difficultés, ou avoir d'autres causes, comme une pause du suivi.",
        "food_silent_market": "Aucun prix n'a été publié pour cette denrée sur ce marché depuis {month}, alors que le "
                              "marché publie encore d'autres denrées et que d'autres marchés {in_country} publient "
                              "encore celle-ci. Cela peut avoir des causes ordinaires, comme la saison ou un changement "
                              "dans ce que le PAM suit ici, mais la denrée est peut-être aussi devenue difficile à "
                              "trouver.",
        "food_silent_country": "Aucun prix n'a été publié pour cette denrée sur ce marché depuis {month}, et aucun "
                               "marché {in_country} ne la publie actuellement. Cela indique un changement dans ce que "
                               "le PAM suit, et non un problème sur ce marché.",
        "food_silent_other_unit": "Aucun prix par {unit} n'a été publié pour cette denrée sur ce marché depuis {month} : "
                                  "le PAM la publie maintenant ici par {other_unit}.",
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
