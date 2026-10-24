def test_local_spark_session_starts(spark):
    """Guards the local PySpark + Java 17 setup that later idempotency tests rely on."""
    assert spark.range(3).count() == 3
