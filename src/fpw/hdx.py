"""Client and payload checks for WFP food prices on HDX (Humanitarian Data Exchange, CKAN API, no key).

License: CC BY-IGO; attribute WFP on every page and download.
"""

import csv
import io
import json

import requests

from fpw import InvalidPayload

HDX_API = "https://data.humdata.org/api/3/action"
USER_AGENT = "food-price-watch (non-commercial early-warning research)"

# Columns of the per-country price CSV, in order (verified on 2026-10-24).
PRICE_COLUMNS = (
    "date", "admin1", "admin2", "market", "market_id", "latitude", "longitude", "category", "commodity",
    "commodity_id", "unit", "priceflag", "pricetype", "currency", "price", "usdprice",
)


def dataset_name(country_slug: str) -> str:
    """HDX dataset name for a country slug as HDX spells it, e.g. 'burkina-faso'."""
    return f"wfp-food-prices-for-{country_slug}"


def fetch(url: str, params: dict | None = None, timeout: int = 120) -> tuple[str, str]:
    """GET a URL, following redirects (HDX downloads redirect to S3). Returns (final URL, body text).

    The final URL is reported without its query string: HDX redirects to pre-signed S3 URLs that carry
    temporary credentials, which must not end up in bronze.
    """
    resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.url.split("?")[0], resp.content.decode("utf-8-sig")


def parse_package(text: str) -> dict:
    """The `result` of a CKAN package_show response; raises InvalidPayload otherwise."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidPayload(f"package_show is not JSON: {text[:80]!r}") from e
    if not isinstance(body, dict) or body.get("success") is not True or not isinstance(body.get("result"), dict):
        raise InvalidPayload(f"package_show was not successful: {text[:80]!r}")
    return body["result"]


def price_resource(package: dict) -> dict:
    """The price CSV resource ('<Country> - Food Prices', with `url` and `last_modified`), not the markets list."""
    found = [
        r for r in package.get("resources", [])
        if r.get("format", "").upper() == "CSV" and r.get("name", "").endswith("Food Prices")
    ]
    if len(found) != 1:
        raise InvalidPayload(f"expected 1 price CSV in {package.get('name')}, found {len(found)}")
    return found[0]


def price_resource_url(package: dict) -> str:
    return price_resource(package)["url"]


def check_price_csv(text: str) -> int:
    """Validate a price CSV payload without parsing it fully; returns the number of data rows.

    Raises InvalidPayload for an empty body, an HTML page (error or unfollowed redirect), a different header,
    or a header without data rows.
    """
    if not text.strip():
        raise InvalidPayload("empty payload")
    if text.lstrip().startswith("<"):
        raise InvalidPayload(f"HTML instead of CSV: {text.strip()[:80]!r}")
    rows = csv.reader(io.StringIO(text))
    header = tuple(next(rows))
    if header != PRICE_COLUMNS:
        raise InvalidPayload(f"unexpected header: {header}")
    n = sum(1 for row in rows if row)
    if n == 0:
        raise InvalidPayload("header without data rows")
    return n
