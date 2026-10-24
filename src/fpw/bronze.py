"""Bronze snapshots: the price CSV exactly as received, stored as a file in a UC Volume, one per change at HDX."""

import hashlib
from datetime import datetime


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def should_download(prev_last_modified: str | None, last_modified: str | None) -> bool:
    """Download only when HDX reports a different resource timestamp than the last stored snapshot (or none)."""
    return prev_last_modified is None or last_modified is None or last_modified != prev_last_modified


def snapshot_path(volume_dir: str, country: str, ingested_at: datetime, digest: str, invalid: bool = False) -> str:
    """e.g. /Volumes/workspace/fpw_dev_bronze/raw/hdx/mali/20261024T131500Z_1a2b3c4d5e6f.csv

    Invalid payloads are stored too (with suffix .invalid), so an outage can be diagnosed from what was received.
    """
    stamp = ingested_at.strftime("%Y%m%dT%H%M%SZ")
    return f"{volume_dir}/hdx/{country}/{stamp}_{digest[:12]}.csv{'.invalid' if invalid else ''}"
