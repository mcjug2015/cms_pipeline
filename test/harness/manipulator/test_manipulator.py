from unittest import mock

from src import custom_logging
from src.harness.manipulator import manipulator
from src.harness.manipulator.manipulator import (
    AbstractBenchmark,
    ClusterRoundtripLatency,
    CollectBandwidth,
    PythonUdfOverhead,
    RangeAggregation,
    ShuffleGroupBy,
    SingleRowInsert,
)

logger = custom_logging.setup_logging().getLogger(__name__)


@mock.patch.multiple(AbstractBenchmark, __abstractmethods__=set())
def test_abstract_benchmark_save_metric(migrated_test_spark):
    bmrk = AbstractBenchmark(
        migrated_test_spark, cat="spark_catalog", schema="default", the_batch_id="7"
    )
    bmrk.save_metric({"testing": "testing"})
    sql_result = migrated_test_spark.sql("select * from spark_catalog.default.metrics;")
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    assert len(results) == 1
    assert results[0]["metric_name"] == "AbstractBenchmark"


@mock.patch.multiple(AbstractBenchmark, __abstractmethods__=set())
@mock.patch("src.harness.manipulator.manipulator.AbstractBenchmark.save_metric")
@mock.patch("src.harness.manipulator.manipulator.AbstractBenchmark.benchmark")
def test_abstract_benchmark_execute(benchmark, save_metric):
    bmrk = AbstractBenchmark(None, cat=None, schema=None, the_batch_id=None)
    bmrk.execute()
    benchmark.assert_called_once()
    save_metric.assert_called_once()


def test_single_row_insert(migrated_test_spark):
    SingleRowInsert(
        migrated_test_spark, cat="spark_catalog", schema="default", the_batch_id="7"
    ).benchmark()
    sql_result = migrated_test_spark.sql(
        "select * from spark_catalog.default.test_table order by int_id desc;"
    )
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    assert len(results) == 1
    assert results[0]["stuff"].startswith("QQPP")
    logger.info("end of test")


def test_cluster_roundtrip_latency(test_spark):
    result = ClusterRoundtripLatency(
        test_spark,
        cat="spark_catalog",
        schema="default",
        the_batch_id="7",
        iterations=1,
    ).benchmark()
    assert result["iterations"] == 1
    assert result["total_seconds"] > 0


def test_range_aggregation(test_spark):
    result = RangeAggregation(
        test_spark, cat="spark_catalog", schema="default", the_batch_id="7", num_rows=1
    ).benchmark()
    assert result["num_rows"] == 1
    assert result["total_seconds"] >= 0


def test_shuffle_group_by(test_spark):
    result = ShuffleGroupBy(
        test_spark,
        cat="spark_catalog",
        schema="default",
        the_batch_id="7",
        num_rows=1,
        num_groups=1,
    ).benchmark()
    assert result["num_rows"] == 1
    assert result["num_groups"] == 1
    assert result["total_seconds"] >= 0


def test_collect_bandwidth(test_spark):
    result = CollectBandwidth(
        test_spark, cat="spark_catalog", schema="default", the_batch_id="7", num_rows=1
    ).benchmark()
    assert result["num_rows"] == 1
    assert result["rows_collected"] == 1
    assert result["total_seconds"] >= 0


def test_python_udf_overhead(test_spark):
    result = PythonUdfOverhead(
        test_spark, cat="spark_catalog", schema="default", the_batch_id="7", num_rows=1
    ).benchmark()
    assert result["num_rows"] == 1
    assert result["total_seconds"] >= 0
    assert result["python_udf_seconds"] >= 0


# Decorators apply bottom-up, so the mocks arrive as arguments in the reverse
@mock.patch("src.harness.manipulator.manipulator.get_spark")
@mock.patch("src.harness.manipulator.manipulator.SingleRowInsert")
@mock.patch("src.harness.manipulator.manipulator.ClusterRoundtripLatency")
@mock.patch("src.harness.manipulator.manipulator.RangeAggregation")
@mock.patch("src.harness.manipulator.manipulator.ShuffleGroupBy")
@mock.patch("src.harness.manipulator.manipulator.CollectBandwidth")
@mock.patch("src.harness.manipulator.manipulator.PythonUdfOverhead")
def test_main_calls_execute_on_benchmarks(
    mock_python_udf_overhead,
    mock_collect_bandwidth,
    mock_shuffle_group_by,
    mock_range_aggregation,
    mock_cluster_roundtrip_latency,
    mock_single_row_insert,
    mock_get_spark,
):
    """main() should invoke .execute() on every benchmark class."""
    manipulator.main(cat="c", schema="s")

    for benchmark_class in (
        mock_single_row_insert,
        mock_cluster_roundtrip_latency,
        mock_range_aggregation,
        mock_shuffle_group_by,
        mock_collect_bandwidth,
        mock_python_udf_overhead,
    ):
        benchmark_class.return_value.execute.assert_called_once()
    mock_get_spark.assert_called_once()
