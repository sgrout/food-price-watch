from pathlib import Path

import pytest

from fpw import InvalidPayload
from fpw.hdx import PRICE_COLUMNS, check_price_csv, dataset_name, parse_package, price_resource_url

DATA = Path(__file__).parent / "data"


def test_dataset_name():
    assert dataset_name("burkina-faso") == "wfp-food-prices-for-burkina-faso"


def test_parse_package_and_price_url_from_real_response():
    package = parse_package((DATA / "hdx_package_show_nga.json").read_text())
    assert package["license_id"] == "cc-by-igo"
    assert price_resource_url(package).endswith("/wfp_food_prices_nga.csv")  # not wfp_markets_nga.csv


@pytest.mark.parametrize("text", ["<html>Service unavailable</html>", '{"success": false, "error": {}}', "[]"])
def test_parse_package_rejects_non_results(text):
    with pytest.raises(InvalidPayload):
        parse_package(text)


def test_price_resource_url_needs_exactly_one_csv():
    with pytest.raises(InvalidPayload):
        price_resource_url({"name": "x", "resources": [{"name": "X - Markets", "format": "CSV", "url": "u"}]})


def test_check_price_csv_accepts_real_download():
    assert check_price_csv((DATA / "wfp_food_prices_mli_head.csv").read_text()) == 20


def test_check_price_csv_rejects_redirect_page():
    # What the download URL returns when redirects are not followed (a real, redacted copy).
    with pytest.raises(InvalidPayload, match="HTML"):
        check_price_csv((DATA / "hdx_redirect_page.html").read_text())


@pytest.mark.parametrize("text", ["", "  \n", ",".join(PRICE_COLUMNS) + "\n", "date,price\n2024-01-15,1\n"])
def test_check_price_csv_rejects_empty_or_changed_format(text):
    with pytest.raises(InvalidPayload):
        check_price_csv(text)
