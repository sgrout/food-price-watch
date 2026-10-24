import os
import sys
from pathlib import Path

import pytest

# Local PySpark needs Java 17. Fall back to Homebrew's openjdk@17 when JAVA_HOME is not set (CI sets it).
_BREW_JDK = Path("/opt/homebrew/opt/openjdk@17")
if "JAVA_HOME" not in os.environ and _BREW_JDK.exists():
    os.environ["JAVA_HOME"] = str(_BREW_JDK)

# Spark's Python workers must use the same interpreter as the driver (the venv), not the system python3.
os.environ["PYSPARK_PYTHON"] = sys.executable


@pytest.fixture(scope="session")
def spark():
    """Local SparkSession, started only by tests that ask for it (most logic is pandas)."""
    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder
        .master("local[1]")
        .appName("fpw-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()

