from unittest import mock

from src import custom_logging
from src.harness.manipulator import manipulator
from src.harness.manipulator.manipulator import (
    benchmark_collect_bandwidth,
    benchmark_python_udf_overhead,
    benchmark_query_round_trip,
    benchmark_range_aggregation,
    benchmark_shuffle,
    with_spark,
)

logger = custom_logging.setup_logging().getLogger(__name__)


def test_with_spark(migrated_test_spark):
    with_spark(migrated_test_spark, cat="spark_catalog", schema="default")
    sql_result = migrated_test_spark.sql(
        "select * from spark_catalog.default.test_table order by int_id desc;"
    )
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    assert len(results) == 1
    assert results[0]["stuff"].startswith("QQPP")
    logger.info("end of test")


def test_benchmark_query_round_trip(test_spark):
    result = benchmark_query_round_trip(
        test_spark, cat="spark_catalog", schema="default", iterations=1
    )
    assert result["iterations"] == 1
    assert result["total_seconds"] > 0


def test_benchmark_range_aggregation(test_spark):
    result = benchmark_range_aggregation(
        test_spark, cat="spark_catalog", schema="default", num_rows=1
    )
    assert result["num_rows"] == 1
    assert result["elapsed_seconds"] >= 0


def test_benchmark_shuffle(test_spark):
    result = benchmark_shuffle(
        test_spark, cat="spark_catalog", schema="default", num_rows=1, num_groups=1
    )
    assert result["num_rows"] == 1
    assert result["num_groups"] == 1
    assert result["elapsed_seconds"] >= 0


def test_benchmark_collect_bandwidth(test_spark):
    result = benchmark_collect_bandwidth(
        test_spark, cat="spark_catalog", schema="default", num_rows=1
    )
    assert result["num_rows"] == 1
    assert result["rows_collected"] == 1
    assert result["elapsed_seconds"] >= 0


def test_benchmark_python_udf_overhead(test_spark):
    result = benchmark_python_udf_overhead(
        test_spark, cat="spark_catalog", schema="default", num_rows=1
    )
    assert result["num_rows"] == 1
    assert result["native_seconds"] >= 0
    assert result["python_udf_seconds"] >= 0


BENCHMARK_NAMES = [
    "benchmark_query_round_trip",
    "benchmark_range_aggregation",
    "benchmark_shuffle",
    "benchmark_collect_bandwidth",
    "benchmark_python_udf_overhead",
]


def test_main():
    mock_spark = mock.MagicMock(name="spark")

    with mock.patch.object(
        manipulator, "get_spark", return_value=mock_spark
    ) as mock_get_spark, mock.patch.multiple(
        manipulator,
        with_spark=mock.DEFAULT,
        benchmark_query_round_trip=mock.DEFAULT,
        benchmark_range_aggregation=mock.DEFAULT,
        benchmark_shuffle=mock.DEFAULT,
        benchmark_collect_bandwidth=mock.DEFAULT,
        benchmark_python_udf_overhead=mock.DEFAULT,
    ) as mocks:
        manipulator.main(cat="c", schema="s")

    mock_get_spark.assert_called_once()
    mocks["with_spark"].assert_called_once_with(mock_spark, "c", "s")
    for name in BENCHMARK_NAMES:
        mocks[name].assert_called_once()
        # main runs each benchmark against the single mocked session.
        assert mocks[name].call_args.args[0] is mock_spark
