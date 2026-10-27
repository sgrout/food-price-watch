"""Plain-language basket texts (English and French), produced by code from facts only (no hand-written numbers).

Numbers follow the shared display rule of fpw.explain (exported precision, half-even on the exact decimal value,
locale separators).
"""

from fpw.explain import display_price
from fpw.texts import COMMODITY_FR, MONTHS, NUMBER_FORMAT

FULL_RATION = ("cereal", "pulses", "oil")  # the components of a full ration basket (config/baskets.csv)

COMPONENT_NAMES = {
    "en": {"cereal": "cereals", "pulses": "pulses", "oil": "cooking oil"},
    "fr": {"cereal": "céréales", "pulses": "légumineuses", "oil": "huile"},
}

TEXTS = {
    "en": {
        "cost": "A staple basket for one person for one month ({composition}) cost about {cost} {currency} in {month}.",
        "forecast": "{Month}: most likely between {lo} and {hi} {currency} (8 in 10 chance).",
        "stale": "No complete basket cost has been published for this market since {month}: {next} is {k} months "
                 "after it, so the range is wider than usual.",
        "missing": "Not included: {missing}; WFP's price series for them here are missing or too short for a "
                   "forecast.",
        "caveat": "This is a simple ration-based basket made by Staple Signals, not an official minimum expenditure "
                  "basket.",
    },
    "fr": {
        "cost": "Un panier de base pour une personne pendant un mois ({composition}) coûtait environ {cost} "
                "{currency} en {month}.",
        "forecast": "{Month} : probablement entre {lo} et {hi} {currency} (8 chances sur 10).",
        "stale": "Aucun coût complet du panier n'a été publié pour ce marché depuis {month} : {next} se situe "
                 "{k} mois plus tard, l'intervalle est donc plus large que d'habitude.",
        "missing": "Non inclus : {missing} ; les séries de prix du PAM sont absentes ou trop courtes ici "
                   "pour une prévision.",
        "caveat": "Il s'agit d'un panier simple fondé sur une ration, établi par Staple Signals, et non d'un panier "
                  "minimum de dépenses officiel.",
    },
}


def quantity_text(q: float, lang: str) -> str:
    """12 -> '12', 1.8 -> '1.8' / '1,8', 0.75 -> '0.75' / '0,75' (no trailing zeros)."""
    s = f"{q:g}"
    return s.replace(".", NUMBER_FORMAT[lang][1])


def composition_text(components: list[dict], lang: str) -> str:
    """'12 kg Millet, 1.8 kg Beans (niebe)' / '12 kg Mil, 1,8 kg Niébé'."""
    parts = []
    for c in components:
        name = COMMODITY_FR.get(c["commodity"], c["commodity"]) if lang == "fr" else c["commodity"]
        parts.append(f"{quantity_text(c['quantity'], lang)} {c['unit'].lower()} {name}")
    return ", ".join(parts)


def missing_components(components: list[dict]) -> list[str]:
    present = {c["component"] for c in components}
    return [c for c in FULL_RATION if c not in present]


def describe_basket(f: dict, lang: str = "en") -> str:
    """f: components, currency, last_month, cost, next_month, next_lo, next_hi, last_fc_month, last_lo, last_hi
    [, data_up_to: adds a note when the last complete cost is older]."""
    t, months = TEXTS[lang], MONTHS[lang]
    month = lambda m: f"{months[m % 12]} {m // 12}"
    cap = lambda s: s[:1].upper() + s[1:]
    price = lambda x: display_price(x, lang)
    parts = [t["cost"].format(composition=composition_text(f["components"], lang), cost=price(f["cost"]),
                              currency=f["currency"], month=month(f["last_month"]))]
    if f.get("next_month") is not None:
        if f["last_month"] < f.get("data_up_to", f["last_month"]):
            parts.append(t["stale"].format(month=month(f["last_month"]), next=month(f["next_month"]),
                                           k=f["next_month"] - f["last_month"]))
        parts.append(t["forecast"].format(Month=cap(month(f["next_month"])), lo=price(f["next_lo"]),
                                          hi=price(f["next_hi"]), currency=f["currency"]))
        parts.append(t["forecast"].format(Month=cap(month(f["last_fc_month"])), lo=price(f["last_lo"]),
                                          hi=price(f["last_hi"]), currency=f["currency"]))
    missing = missing_components(f["components"])
    if missing:
        parts.append(t["missing"].format(missing=", ".join(COMPONENT_NAMES[lang][m] for m in missing)))
    parts.append(t["caveat"])
    return " ".join(parts)
