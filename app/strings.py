"""App labels (English). Explanations come from the pipeline (fpw.texts); these are only UI labels."""

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# Status: fixed status palette, always shown with an icon and a label (never colour alone).
STATUS = {
    "normal": ("✓", "Normal", "#0ca30c"),
    "stress": ("▲", "Stress", "#fab219"),
    "alert": ("▲▲", "Alert", "#ec835a"),
    "crisis": ("■", "Crisis", "#d03b3b"),
}

ATTRIBUTION = ("Data: World Food Programme (WFP), via the Humanitarian Data Exchange (HDX), CC BY-IGO. "
               "Forecasts: Staple Signals (not an official WFP or FEWS NET assessment). "
               "Official assessments: [WFP HungerMap](https://hungermap.wfp.org) · [FEWS NET](https://fews.net).")

TITLE = "Staple Signals"
NOT_ELIGIBLE = ("Not enough data for a forecast: a series needs at least 5 years of mostly complete, recent prices. "
                "Prices are shown without a forecast.")


def month_label(m: int) -> str:
    """Month index (months since year 0, as in fpw.panel) -> 'October 2026'."""
    return f"{MONTHS[int(m) % 12]} {int(m) // 12}"


def skill_verdict(score: float, base_rate_score: float, margin: float = 0.03) -> str:
    """Plain verdict on a Brier score against the base-rate score (lower is better), within +-3 % = no difference."""
    ratio = score / base_rate_score
    if ratio < 1 - margin:
        return "better than the base rate"
    if ratio > 1 + margin:
        return "worse than the base rate"
    return "no better than the base rate"
