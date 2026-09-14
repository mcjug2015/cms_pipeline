"""Register the migrate stage's Delta tables in the serve stage's Hive metastore.

The migrate stage runs the chain through spark_sql_migrations' get_spark(),
which never enables Hive support, so its catalog lives in memory and dies with
that JVM: only the Delta table directories under the warehouse survive the
COPY. This re-attaches each of them, in place, to the persistent Derby-backed
catalog the Connect server uses. A Delta table's schema lives in its own
_delta_log, so `CREATE TABLE ... USING delta LOCATION` restores it exactly
without restating any DDL here.

Run with the image's own spark-submit, after spark-defaults.conf is in place:

    spark-submit register_tables.py <catalog> <schema> <warehouse_dir>

Not a Pants target: it only ever runs inside docker/spark-migrated's build, against
the base image's Spark, not this repo's resolves.
"""

import os
import sys

from pyspark.sql import SparkSession


def tables_dir(warehouse_dir, schema):
    # Spark's layout: `default` lives at the warehouse root, every other schema
    # in a <schema>.db subdirectory.
    return warehouse_dir if schema == "default" else os.path.join(warehouse_dir, f"{schema}.db")


def main(cat, schema, warehouse_dir):
    spark = SparkSession.builder.enableHiveSupport().getOrCreate()
    spark.sql(f"create schema if not exists {cat}.{schema}")

    root = tables_dir(warehouse_dir, schema)
    registered = []
    for name in sorted(os.listdir(root)):
        location = os.path.join(root, name)
        if os.path.isdir(os.path.join(location, "_delta_log")):
            spark.sql(f"create table if not exists {cat}.{schema}.`{name}` using delta location '{location}'")
            registered.append(name)

    # An empty store means the migrate stage silently produced nothing; fail the
    # build rather than export an image that looks migrated and isn't.
    if not registered:
        sys.exit(f"no Delta tables found under {root}")
    print(f"registered in {cat}.{schema}: {', '.join(registered)}")

    # A clean stop shuts Derby down, so no stale lock files ship in the image.
    spark.stop()


if __name__ == "__main__":
    main(*sys.argv[1:4])
