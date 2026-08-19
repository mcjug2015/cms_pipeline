import os
import sys

from delta import configure_spark_with_delta_pip  # type: ignore
from pyspark.sql.session import SparkSession


def is_dbr():
    try:
        from pyspark.dbutils import DBUtils  # type: ignore # noqa: F401

        # This will only succeed if the Databricks environment is available
        return True  # pragma: no cover
    except Exception:
        return False


def get_spark(use_dbc=False):
    if use_dbc or is_dbr():
        from databricks.connect.session import DatabricksSession  # type: ignore

        os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"
        return DatabricksSession.builder.getOrCreate()

    spark_remote = os.environ.get("SPARK_REMOTE")
    if spark_remote:
        return SparkSession.builder.remote(spark_remote).getOrCreate()

    # Pin the worker interpreter to the one actually running this process. Left
    # unset, Spark resolves "python3" independently for the worker daemon, which
    # can land on a different Python build than the driver's when launched from
    # an IDE (mismatched sys.executable vs. PATH resolution) -- causing worker
    # crashes like "SRE module mismatch" that don't reproduce from the CLI.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

    warehouse_dir = os.environ.get(
        "SPARK_WAREHOUSE_DIR",
        os.path.join(os.path.dirname(__file__), "..", "spark-warehouse"),
    )
    builder = (
        SparkSession.builder.appName("Testing PySpark Example")
        .config("spark.sql.warehouse.dir", warehouse_dir)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.sources.default", "delta")
    )
    metastore_dir = os.environ.get("SPARK_METASTORE_DIR")
    if metastore_dir:
        builder = builder.config(
            "javax.jdo.option.ConnectionURL",
            f"jdbc:derby:;databaseName={metastore_dir};create=true",
        )
    return configure_spark_with_delta_pip(builder).getOrCreate()
