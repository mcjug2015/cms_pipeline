# syntax=docker/dockerfile:1
#
# A Spark Connect server with this repo's all_spark_migrations chain already applied.
#
#   migrate  applies the chain with a throwaway local Delta Spark, leaving Delta
#            table directories under /opt/spark-store.
#   serve    the published image: the spark-connect base plus that store, with each
#            table registered in a Derby-backed Hive metastore so clients find it.
#
# The store has the same absolute path in both stages on purpose: the metastore
# records each table's LOCATION, so moving the store would orphan every table.
#
# Build from the repo root (the migration chains are the context);
# scripts/build_migrated_image.sh does that and builds the base image first.

ARG BASE_IMAGE=spark-connect-test:4.1.0


FROM python:3.12.3-slim-bookworm AS migrate


RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pyspark[connect]==4.1.0" "delta-spark==4.3.1" "spark_sql_migrations[local]==0.0.2"


COPY src/crutch_migrations/all_spark_migrations /migrations/all_spark_migrations


RUN SPARK_WAREHOUSE_DIR=/opt/spark-store/warehouse \
    spark-sql-migrations run --cat=spark_catalog --schema=default --migrations-dir=/migrations


FROM ${BASE_IMAGE} AS serve

USER root

COPY --from=migrate /opt/spark-store /opt/spark-store

# In spark-defaults rather than the CMD so the Connect server, spark-submit and
# spark-sql all see the migrated store (Derby allows one JVM at a time, so use one
# per container). catalogImplementation=hive is what makes the metastore
# persistent. The Derby URL needs the spark.hadoop. prefix: spark-defaults.conf
# ignores non-spark.* keys.
RUN mkdir -p /opt/spark/conf && cat > /opt/spark/conf/spark-defaults.conf <<'EOF'
spark.jars.packages org.apache.spark:spark-connect_2.13:4.1.0,io.delta:delta-spark_4.1_2.13:4.3.1
spark.jars.ivy /opt/spark/work-dir/ivy
spark.sql.extensions io.delta.sql.DeltaSparkSessionExtension
spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog
spark.sql.sources.default delta
spark.sql.catalogImplementation hive
spark.sql.warehouse.dir /opt/spark-store/warehouse
spark.hadoop.javax.jdo.option.ConnectionURL jdbc:derby:;databaseName=/opt/spark-store/metastore_db;create=true
EOF

# Re-attach the migrate stage's Delta tables to the metastore. Running under the
# spark-defaults above also resolves the jars into the ivy dir, so the server
# starts without Maven. This runs as root, hence the chmod so both `USER spark`
# and CI's --user 0:0 can use the store and the jars.
RUN --mount=type=bind,source=docker/spark-migrated/register_tables.py,target=/tmp/register_tables.py \
    cd /tmp \
    && /opt/spark/bin/spark-submit --master "local[1]" /tmp/register_tables.py \
        spark_catalog default /opt/spark-store/warehouse \
    && chmod -R 0777 /opt/spark-store /opt/spark/work-dir/ivy

LABEL org.opencontainers.image.source="https://github.com/mcjug2015/cms_pipeline" \
      org.opencontainers.image.description="Spark Connect server pre-migrated to cms_pipeline's all_spark_migrations chain" \
      io.cms-pipeline.migrated.catalog="spark_catalog" \
      io.cms-pipeline.migrated.schema="default"

USER spark
EXPOSE 15002
CMD ["/opt/spark/sbin/start-connect-server.sh", "--wait"]
