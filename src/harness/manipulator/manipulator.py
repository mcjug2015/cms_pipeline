import argparse
import os
import shutil
import time

from pyspark.sql import SparkSession

from src import custom_logging
from src.crutch_migrations.run_crutch_migrations import run_migrations
from src.spark_utils import get_spark


logger = custom_logging.setup_logging().getLogger(__name__)


def with_spark(spark: SparkSession, cat: str, schema: str):
    spark.sql(
        f"""
        insert into {cat}.{schema}.test_table(int_id, stuff) values ({time.time_ns()}, 'zoop zoop');
    """
    )
    sql_result = spark.sql(
        f"select * from {cat}.{schema}.test_table order by int_id desc;"
    )
    [
        logger.info(f"test table row is: {x.asDict()}")
        for x in sql_result.toLocalIterator()
    ]


def main(spark, cat, schema):
    logger.info("begin manipulator main")
    with_spark(spark, cat, schema)
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
    spark = get_spark()
    run_migrations(spark, cat=args.cat, schema=args.schema)
    main(spark, cat=args.cat, schema=args.schema)
