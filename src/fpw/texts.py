"""User-facing text templates (string catalog). English first; add a language by adding a dict with the same keys.

Templates only take numbers from `fpw.explain` facts: no number is ever written by hand or by an LLM.
"""

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
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
        "market_up": "Across {n} {group} markets in {country}, the median price rose {pct}% over those 3 months.",
        "market_down": "Across {n} {group} markets in {country}, the median price fell {pct}% over those 3 months.",
        "market_flat": "Across {n} {group} markets in {country}, the median price was about stable.",
        "forecast": "{month}: most likely between {lo} and {hi} {currency}/{unit} (8 in 10 chance).",
        "spike": "Chance of a spike in {month} (price well above the usual level for the season): {p}%.",
        "caveat": "Warnings of new spikes have no proven skill yet (track record 2023-2026).",
    },
}
