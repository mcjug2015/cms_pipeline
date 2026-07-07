import argparse
import datetime
import os
import shutil
import sys
import time
from typing import Any, Dict

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType

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


def benchmark_query_round_trip(
    spark: SparkSession, iterations: int = 50
) -> Dict[str, Any]:
    """Benchmark driver<->cluster round-trip latency using trivial no-op queries.

    Runs many minimal ``select 1`` queries so the measured time is dominated by
    request/response overhead rather than computation, exposing how "chatty" the
    connection to this particular spark instance is.
    """
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        spark.sql("select 1").collect()
        durations.append(time.perf_counter() - start)
    durations.sort()
    total = sum(durations)
    metrics = {
        "iterations": iterations,
        "total_seconds": total,
        "avg_ms": (total / iterations) * 1000,
        "min_ms": durations[0] * 1000,
        "p50_ms": durations[len(durations) // 2] * 1000,
        "p95_ms": durations[min(len(durations) - 1, int(len(durations) * 0.95))] * 1000,
        "max_ms": durations[-1] * 1000,
    }
    logger.info(f"[benchmark] query round-trip latency: {metrics}")
    return metrics


def benchmark_range_aggregation(
    spark: SparkSession, num_rows: int = 50_000_000
) -> Dict[str, Any]:
    """Benchmark raw compute throughput via a full-scan aggregation.

    A single-pass ``sum`` over ``spark.range`` is CPU/scan bound with no shuffle
    or data transfer to the driver, so it isolates the cluster's per-row compute
    rate. The checksum is returned to prevent the optimizer eliding the work.
    """
    start = time.perf_counter()
    result = (
        spark.range(0, num_rows).select(F.sum(F.col("id")).alias("total")).collect()
    )
    elapsed = time.perf_counter() - start
    metrics = {
        "num_rows": num_rows,
        "elapsed_seconds": elapsed,
        "rows_per_second": num_rows / elapsed if elapsed else float("inf"),
        "checksum": result[0]["total"] if result else None,
    }
    logger.info(f"[benchmark] range aggregation throughput: {metrics}")
    return metrics


def benchmark_shuffle(
    spark: SparkSession, num_rows: int = 20_000_000, num_groups: int = 1000
) -> Dict[str, Any]:
    """Benchmark shuffle/exchange performance via a wide group-by.

    Grouping many rows into ``num_groups`` buckets forces a shuffle across the
    cluster, stressing network and disk between executors rather than scan speed,
    which is where distributed spark instances differ most.
    """
    start = time.perf_counter()
    grouped = (
        spark.range(0, num_rows)
        .withColumn("grp", F.col("id") % num_groups)
        .groupBy("grp")
        .agg(
            F.count(F.lit(1)).alias("cnt"),
            F.sum(F.col("id")).alias("s"),
        )
    )
    collected = grouped.collect()
    elapsed = time.perf_counter() - start
    metrics = {
        "num_rows": num_rows,
        "num_groups": num_groups,
        "groups_returned": len(collected),
        "elapsed_seconds": elapsed,
        "rows_per_second": num_rows / elapsed if elapsed else float("inf"),
    }
    logger.info(f"[benchmark] shuffle group-by: {metrics}")
    return metrics


def benchmark_collect_bandwidth(
    spark: SparkSession, num_rows: int = 1_000_000
) -> Dict[str, Any]:
    """Benchmark result-transfer bandwidth from executors back to the driver.

    Materializing a payload column and pulling every row to the driver with
    ``collect`` measures serialization + network cost of moving data out of the
    cluster, the opposite bottleneck from the compute-bound benchmarks.
    """
    # md5 yields a stable 32-char hex string per row for a predictable payload size.
    df = spark.range(0, num_rows).withColumn(
        "payload", F.md5(F.col("id").cast("string"))
    )
    start = time.perf_counter()
    rows = df.collect()
    elapsed = time.perf_counter() - start
    approx_bytes = len(rows) * (8 + 32)  # 8-byte long + 32-char payload, rough estimate
    metrics = {
        "num_rows": num_rows,
        "rows_collected": len(rows),
        "elapsed_seconds": elapsed,
        "rows_per_second": len(rows) / elapsed if elapsed else float("inf"),
        "approx_mb_per_second": (
            (approx_bytes / 1e6) / elapsed if elapsed else float("inf")
        ),
    }
    logger.info(f"[benchmark] collect bandwidth: {metrics}")
    return metrics


def benchmark_python_udf_overhead(
    spark: SparkSession, num_rows: int = 5_000_000
) -> Dict[str, Any]:
    """Benchmark the cost of Python UDF serialization vs. native expressions.

    The same squaring computation is run once with a built-in column expression
    and once with a Python UDF; the ratio quantifies the per-row JVM<->Python
    round-trip overhead for this spark instance's worker configuration.
    """
    start = time.perf_counter()
    spark.range(0, num_rows).select((F.col("id") * F.col("id")).alias("v")).agg(
        F.sum(F.col("v"))
    ).collect()
    native_elapsed = time.perf_counter() - start

    square_udf = F.udf(lambda x: x * x, LongType())
    start = time.perf_counter()
    spark.range(0, num_rows).select(square_udf(F.col("id")).alias("v")).agg(
        F.sum(F.col("v"))
    ).collect()
    udf_elapsed = time.perf_counter() - start

    metrics = {
        "num_rows": num_rows,
        "native_seconds": native_elapsed,
        "python_udf_seconds": udf_elapsed,
        "udf_overhead_ratio": (
            udf_elapsed / native_elapsed if native_elapsed else float("inf")
        ),
    }
    logger.info(f"[benchmark] python UDF overhead: {metrics}")
    return metrics


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
    spark = get_spark()
    with_spark(spark, cat, schema)
    logger.info(
        f"benchmark_query_round_trip says: {benchmark_query_round_trip(spark, iterations=5)}"
    )
    logger.info(
        f"benchmark_range_aggregation says: {benchmark_range_aggregation(spark, num_rows=5000)}"
    )
    logger.info(
        f"benchmark_shuffle says: {benchmark_shuffle(spark, num_rows=5000, num_groups=2)}"
    )
    logger.info(
        f"benchmark_collect_bandwidth says: {benchmark_collect_bandwidth(spark, num_rows=5000)}"
    )
    logger.info(
        f"benchmark_python_udf_overhead says: {benchmark_python_udf_overhead(spark, num_rows=5000)}"
    )
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
