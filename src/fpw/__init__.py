"""food-price-watch: pure logic (no widgets, no table names). Notebooks in src/ handle I/O."""


class InvalidPayload(ValueError):
    """A source returned something that is not the expected format (error page, redirect page, empty file, ...).

    The pipeline skips and logs such payloads, keeps the last good data, and lets the freshness check decide
    whether the source has been stale for too long.
    """
