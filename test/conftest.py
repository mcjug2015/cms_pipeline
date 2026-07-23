import os

import pytest  # type: ignore

from src.crutch_migrations.run_crutch_migrations import (
    get_output_folder,
    run_migrations,
)
from src.spark_utils import get_spark


@pytest.fixture(scope="session", autouse=True)
def _isolated_spark_storage(tmp_path_factory):
    base = tmp_path_factory.mktemp("spark_store")
    os.environ["SPARK_WAREHOUSE_DIR"] = str(base / "warehouse")
    os.environ["SPARK_METASTORE_DIR"] = str(base / "metastore_db")
    yield


# should be possible to isolate per test if needed
@pytest.fixture(scope="session")
def test_spark():
    yield get_spark()


@pytest.fixture(scope="session")
def migrated_test_spark(test_spark):
    output_folder = get_output_folder(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_migrations_out")
    )
    # lets run migrations twice to catch some of the idempotency problems that might exists
    run_migrations(
        test_spark, cat="spark_catalog", schema="default", output_folder=output_folder
    )
    run_migrations(
        test_spark, cat="spark_catalog", schema="default", output_folder=output_folder
    )

    yield test_spark
