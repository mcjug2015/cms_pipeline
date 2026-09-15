# Only the project-owned chains live here. spark_sql_migrations ships the engine,
# migrations_initial/ and migration_templates/ inside its own wheel.
resources(
    name="all_spark_migrations",
    sources=["all_spark_migrations/*.sql"],
)

resources(
    name="dbr_only_migrations",
    sources=["dbr_only_migrations/*.sql"],
)

# spark_sql_migrations' own console command, once per resolve. `pants run` runs a
# pex_binary in a sandbox, so --migrations-dir and --output-path must be absolute.
#
# python-default pulls databricks-connect, whose pyspark.dbutils makes is_dbr()
# true, so this one targets Databricks -- CI's "Apply ddl" step runs it.
pex_binary(
    name="spark-sql-migrations",
    script="spark-sql-migrations",
    dependencies=[
        "src:reqs#spark_sql_migrations",
        "src:reqs#databricks-connect",
    ],
)

# py-reqs-dev pulls OSS pyspark instead, so this one targets local Spark or, with
# SPARK_REMOTE set, a Spark Connect server (scripts/migrated_spark.sh).
pex_binary(
    name="spark-sql-migrations-local",
    script="spark-sql-migrations",
    resolve="py-reqs-dev",
    dependencies=["test:reqs-dev#spark_sql_migrations"],
)
