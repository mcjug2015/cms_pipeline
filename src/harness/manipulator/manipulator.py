import argparse
import datetime
import os
import shutil
import sys
import time

from pyspark.sql import SparkSession

from src import custom_logging
from src.crutch_migrations.run_crutch_migrations import (
    get_ascending_letters_within_minute,
)
from src.spark_utils import get_spark

logger = custom_logging.setup_logging().getLogger(__name__)


def with_spark(spark: SparkSession, cat: str, schema: str):
    stuff = f"QQPP{datetime.datetime.today().strftime('%Y%m%d_%H%M')}_{get_ascending_letters_within_minute()}"
    spark.sql(
        f"""
        insert into {cat}.{schema}.test_table(int_id, stuff) values ({time.time_ns()}, '{stuff}');
    """
    )
    sql_result = spark.sql(
        f"select * from {cat}.{schema}.test_table order by int_id desc;"
    )
    [
        logger.info(f"test table row is: {x.asDict()}")
        for x in sql_result.toLocalIterator()
    ]


def main(*args, **kwargs):
    logger.info("begin manipulator main")
    cat = kwargs.get("cat", None)
    schema = kwargs.get("schema", None)
    if not cat or not schema:
        cat = sys.argv[1]
        schema = sys.argv[2]
    if not cat or not schema:
        raise ValueError(
            f"Expecting both cat and schema but got {args}, {kwargs}, {sys.argv};"
        )
    with_spark(get_spark(), cat, schema)
    logger.info("end manipulator main")


if __name__ == "__main__":
    shutil.rmtree(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "spark-warehouse"),
        ignore_errors=True,
    )
    parser = argparse.ArgumentParser(description="manipulator params")
    parser.add_argument(
        "--cat",
        help="catalog name to use",
        default="spark_catalog",
    )
    parser.add_argument(
        "--schema",
        help="schema name to use",
        default="default",
    )
    args = parser.parse_args()
    main(cat=args.cat, schema=args.schema)
