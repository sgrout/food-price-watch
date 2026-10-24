from datetime import datetime, timezone

from fpw.bronze import sha256, should_download, snapshot_path


def test_should_download_only_when_hdx_reports_a_change():
    assert should_download(None, "2026-10-18T20:23:00")
    assert not should_download("2026-10-18T20:23:00", "2026-10-18T20:23:00")
    assert should_download("2026-10-18T20:23:00", "2026-10-25T20:00:00")
    assert should_download("2026-10-18T20:23:00", None)  # no timestamp: download and compare hashes instead


def test_snapshot_path():
    t = datetime(2026, 10, 24, 13, 15, 0, tzinfo=timezone.utc)
    digest = sha256("x")
    assert snapshot_path("/Volumes/workspace/fpw_dev_bronze/raw", "mali", t, digest) == (
        f"/Volumes/workspace/fpw_dev_bronze/raw/hdx/mali/20261024T131500Z_{digest[:12]}.csv")
    assert snapshot_path("/v", "mali", t, digest, invalid=True).endswith(".csv.invalid")
