import os


def is_dbr():
    try:
        from pyspark.dbutils import DBUtils

        # This will only succeed if the Databricks environment is available
        return True
    except Exception:
        return False


def get_spark(use_dbc=False):
    if use_dbc:
        from databricks.connect.session import DatabricksSession

        os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"
        return DatabricksSession.builder.getOrCreate()
    from pyspark.sql.session import SparkSession

    spark = (
        SparkSession.builder.appName("Testing PySpark Example")
        .config(
            "spark.sql.warehouse.dir",
            os.path.join(os.path.dirname(__file__), "..", "spark-warehouse"),
        )
        .getOrCreate()
    )
    return spark
