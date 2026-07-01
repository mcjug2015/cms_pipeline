import os
import shutil

import pytest  # type: ignore

from src.crutch_migrations.run_crutch_migrations import (get_output_folder,
                                                         run_migrations)
from src.spark_utils import get_spark


@pytest.fixture
def spark():
    shutil.rmtree(
        os.path.join(os.path.dirname(__file__), "..", "spark-warehouse"),
        ignore_errors=True,
    )
    spark = get_spark()
    yield spark


@pytest.fixture
def migrated_spark(spark):
    output_folder = get_output_folder(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_migrations_out")
    )
    run_migrations(
        spark, cat="spark_catalog", schema="default", output_folder=output_folder
    )

    yield spark
