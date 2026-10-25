import re

import numpy as np
import pandas as pd

from fpw.explain import describe, display_pct, display_price, facts, status
from fpw.texts import MONTHS, TEXTS


def rows(resid=0.3, ret3=0.25, grp=-0.1, n=12, spike=0.42):
    steps = [1, 2, 3, 4, 5]
    lp = np.log(500.0)
    return pd.DataFrame({
        # step s targets the last usable month + s
        "step": steps, "target": [2026 * 12 + 7 + s for s in steps], "m_last": 2026 * 12 + 7, "z_now": resid / 0.15,
        "resid_last": resid, "ret3": ret3, "grp_ret3": grp, "grp_n": n, "commodity_group": "millet", "country": "burkina-faso",
        "unit": "KG", "q10": lp - 0.1, "q90": lp + 0.2, "spike_prob": spike,
    })


def test_status_thresholds_are_alps_style():
    assert [status(z) for z in [-1, 0.1, 0.25, 0.99, 1.0, 1.99, 2.0]] == \
        ["normal", "normal", "stress", "stress", "alert", "alert", "crisis"]


def test_text_reads_well_and_uses_only_facts():
    f = facts(rows(), currency="XOF")
    text = describe(f)
    assert text.startswith("In August 2026 the price was 35% above the usual level for that time of year (crisis).")
    assert "It rose 28% over the 3 months before." in text
    assert "Across 12 millet markets in Burkina Faso, the median price fell 10% over those 3 months." in text
    assert "November 2026: most likely between 452 and 611 XOF/KG (8 in 10 chance)." in text
    assert "Chance of a spike in November 2026" in text and ": 42%." in text
    assert "no proven skill yet" in text


def test_every_number_in_the_text_comes_from_the_facts():
    """Guardrail: numbers can only come from facts (or the fixed caveat years), never be invented."""
    for args in [dict(), dict(resid=-0.2, ret3=-0.3, grp=0.004, n=1, spike=0.07), dict(resid=0.01, ret3=np.nan)]:
        f = facts(rows(**args), currency="XOF")
        allowed = {str(abs(v)) for v in f.values() if isinstance(v, int)}
        allowed |= {str(m // 12) for m in (f["data_month"], f["next_month"], f["last_month"])}
        allowed |= {f"{x:,.0f}" for x in (f["next_lo"], f["next_hi"], f["last_lo"], f["last_hi"])}
        allowed |= {str(int(round(100 * f["next_spike"]))), "3", "8", "10", "2023", "2026"}  # template constants
        numbers = re.findall(r"\d[\d,]*", describe(f))
        assert set(numbers) <= allowed, set(numbers) - allowed


def test_flat_changes_and_single_market():
    text = describe(facts(rows(resid=0.01, ret3=0.005, n=1), currency="XOF"))
    assert "at the usual level" in text and "about stable" in text and "markets in" not in text


def test_every_language_has_every_key():
    keys = set(TEXTS["en"])
    for lang, t in TEXTS.items():
        assert set(t) == keys and len(MONTHS[lang]) == 12


def test_display_rule_is_half_even_with_price_bands():
    """Shared with the site (docs/export-contract.md section 3): same exported number -> same text."""
    assert [display_price(x) for x in [1250.0, 452.5, 453.5, 45.25, 45.35, 7.125]] == \
        ["1,250", "452", "454", "45.2", "45.4", "7.12"]
    assert [display_pct(p) for p in [0.125, 0.135, 0.42, 0.005]] == ["12", "14", "42", "0"]


def test_text_uses_the_exported_precision():
    # 0.12541 is published as 0.125, which the site shows as 12 %: the text must say 12 %, not 13 %.
    f = facts(rows(spike=0.12541), currency="XOF")
    assert f["next_spike"] == 0.125 and ": 12%." in describe(f)
    assert f["next_lo"] == round(f["next_lo"], 2)
