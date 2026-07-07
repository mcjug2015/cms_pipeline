import os
import shutil

import pytest  # type: ignore

from src.crutch_migrations.run_crutch_migrations import (
    get_output_folder,
    run_migrations,
)
from src.spark_utils import get_spark


@pytest.fixture
def test_spark():
    shutil.rmtree(
        os.path.join(os.path.dirname(__file__), "..", "spark-warehouse"),
        ignore_errors=True,
    )
    yield get_spark()


@pytest.fixture
def migrated_test_spark(test_spark):
    output_folder = get_output_folder(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_migrations_out")
    )
    run_migrations(
        test_spark, cat="spark_catalog", schema="default", output_folder=output_folder
    )

    yield test_spark
