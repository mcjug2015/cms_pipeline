import datetime
import os
import random
import string

import pytest  # type: ignore

from src.crutch_migrations.run_crutch_migrations import (
    get_ascending_letters_within_minute,
    get_output_folder,
    run_migrations,
)
from src.spark_utils import get_spark

SPARK_CONNECT_PORT = 15002


@pytest.fixture(scope="session")
def _spark_connect_remote():
    """Point SPARK_REMOTE at the Spark Connect server on SPARK_CONNECT_PORT.
    Assumes it's already running (started separately, outside of pytest)."""
    host = os.environ.get("SPARK_CONNECT_HOST", "localhost")
    os.environ["SPARK_REMOTE"] = f"sc://{host}:{SPARK_CONNECT_PORT}"
    yield


# should be possible to isolate per test if needed
@pytest.fixture(scope="session")
def test_spark(_spark_connect_remote):
    yield get_spark()


def _migrate_schema(spark, schema):
    output_folder = get_output_folder(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_migrations_out")
    )
    # lets run migrations twice to catch some of the idempotency problems that might exists
    run_migrations(
        spark, cat="spark_catalog", schema=schema, output_folder=output_folder
    )
    run_migrations(
        spark, cat="spark_catalog", schema=schema, output_folder=output_folder
    )


@pytest.fixture(scope="session")
def migrated_spark(test_spark):
    schema_name = f"b_{datetime.datetime.today().strftime('%Y%m%d_%H%M')}"
    schema_name += f"_{get_ascending_letters_within_minute()}"
    schema_name += f"_{''.join(random.choices(string.ascii_letters, k=6))}"
    _migrate_schema(test_spark, schema_name)
    yield (test_spark, schema_name)
