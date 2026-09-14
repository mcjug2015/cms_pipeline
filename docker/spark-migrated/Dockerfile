# syntax=docker/dockerfile:1
#
# A Spark Connect server whose Delta warehouse and Derby metastore already have
# this repo's all_spark_migrations chain applied, start to finish.
#
# Stage 1 (`migrate`) spins up a clean, throwaway local Delta Spark -- pip
# pyspark + delta-spark, pinned to the same versions as test/requirements-dev.txt
# -- and runs src/crutch_migrations end to end against an empty store at
# /opt/spark-store. is_dbr() is false there, so only all_spark_migrations/ is
# applied; dbr_only_migrations/ is Databricks-only and deliberately skipped.
#
# get_spark() never enables Hive support, so stage 1's catalog is in memory and
# dies with its JVM: what carries over is the Delta table directories, not the
# table definitions.
#
# Stage 2 (`serve`) is the exported image: the spark-connect base with that
# finished store copied in, a Hive catalog on a Derby metastore configured in
# spark-defaults.conf, and each Delta table from stage 1 registered in that
# metastore at build time (register_tables.py). A client that points
# SPARK_REMOTE at it finds the migrated tables already there.
#
# The store's absolute path is identical in both stages on purpose: the Delta
# directories are registered where stage 1 wrote them, and the metastore records
# each table's LOCATION absolutely, so moving the store would orphan every table.
#
# Build from the REPO ROOT (the migration chains are part of the context):
#
#   docker build -t cms-pipeline-spark-migrated:local \
#     -f docker/spark-migrated/Dockerfile .
#
#   docker run -d -p 15002 cms-pipeline-spark-migrated:local
#
# scripts/build_migrated_image.sh wraps this, including building the base image
# first. See also .dockerignore, which keeps the root context small.

ARG BASE_IMAGE=spark-connect-test:4.1.0
ARG SPARK_VERSION=4.1.0
ARG SCALA_VERSION=2.13
ARG DELTA_VERSION=4.3.1
ARG DELTA_SCALA_ARTIFACT=delta-spark_4.1_2.13

# The store lives at the same absolute path in both stages -- see the note above.
ARG SPARK_STORE_DIR=/opt/spark-store

# What the chain is applied to. Declared once here so `migrate` (which applies
# it) and `serve` (which registers and labels the tables) can never disagree.
# spark_catalog is the only catalog local OSS Spark has; `default` matches
# run_crutch_migrations.py's own argparse defaults.
ARG MIGRATION_CAT=spark_catalog
ARG MIGRATION_SCHEMA=default


FROM python:3.12.3-slim-bookworm AS migrate

ARG SPARK_VERSION
ARG DELTA_VERSION
ARG SPARK_STORE_DIR

# pyspark launches a JVM; nothing else here needs a toolchain.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# Versions match test/requirements-dev.txt. spark_sql_migrations declares no
# Spark of its own, so [local] is what selects the OSS flavour (the [databricks]
# extra used by src/requirements.txt would pull databricks-connect, which ships
# its own conflicting top-level pyspark/).
RUN pip install --no-cache-dir \
        "pyspark[connect]==${SPARK_VERSION}" \
        "delta-spark==${DELTA_VERSION}" \
        "spark_sql_migrations[local]==0.0.1"

WORKDIR /app
COPY src/__init__.py src/__init__.py
COPY src/crutch_migrations src/crutch_migrations
ENV PYTHONPATH=/app

# Read by spark_sql_migrations.spark_utils.get_spark() to place the warehouse
# instead of a cwd-relative default. SPARK_METASTORE_DIR is deliberately unset:
# without Hive support the catalog is in memory regardless, and stage 2 owns the
# only real metastore.
ENV SPARK_WAREHOUSE_DIR="${SPARK_STORE_DIR}/warehouse"

# Pulled in only here, not at the top of the stage: an ARG in scope is part of
# every later RUN's cache key, so retargeting the schema re-runs just this layer
# rather than the apt and pip installs above.
ARG MIGRATION_CAT
ARG MIGRATION_SCHEMA

# The migration engine resolves the Delta jars from Maven here, so this layer
# needs network.
RUN python -m src.crutch_migrations.run_crutch_migrations \
        run --cat="${MIGRATION_CAT}" --schema="${MIGRATION_SCHEMA}" \
    && chmod -R 0777 "${SPARK_STORE_DIR}"


FROM ${BASE_IMAGE} AS serve

ARG SPARK_VERSION
ARG SCALA_VERSION
ARG DELTA_VERSION
ARG DELTA_SCALA_ARTIFACT
ARG SPARK_STORE_DIR

USER root

ENV SPARK_STORE_DIR="${SPARK_STORE_DIR}"
ENV SPARK_IVY_DIR=/opt/spark/work-dir/ivy

# Resolve the Connect and Delta jars at build time so the exported image starts
# without reaching Maven -- unlike the CI/local containers, which mount a shared
# ivy cache and resolve on every start. Done before spark-defaults.conf exists so
# this throwaway job runs plain, without booting Delta or Derby against the store.
RUN --mount=type=tmpfs,target=/tmp/ivy-work \
    printf 'pass\n' > /tmp/ivy-work/noop.py \
    && /opt/spark/bin/spark-submit \
        --master "local[1]" \
        --packages "org.apache.spark:spark-connect_${SCALA_VERSION}:${SPARK_VERSION},io.delta:${DELTA_SCALA_ARTIFACT}:${DELTA_VERSION}" \
        --conf "spark.jars.ivy=${SPARK_IVY_DIR}" \
        /tmp/ivy-work/noop.py \
    && chmod -R 0777 "${SPARK_IVY_DIR}"

COPY --from=migrate --chmod=0777 ${SPARK_STORE_DIR} ${SPARK_STORE_DIR}

# Baked into spark-defaults rather than the CMD so `spark-sql`, `spark-submit`
# and an exec'd shell all see the same migrated store as the Connect server.
# Derby permits exactly one JVM in the metastore at a time, so use only one of
# them per container.
#
# catalogImplementation=hive is what makes the metastore real: the Connect
# server otherwise defaults to an in-memory catalog, exactly like stage 1. The
# base image ships the Hive jars it needs. The Derby URL needs the spark.hadoop.
# prefix: spark-defaults.conf drops non-spark.* keys ("Ignoring non-Spark config
# property"). The base image also ships no conf/ directory at all.
RUN mkdir -p /opt/spark/conf && cat > /opt/spark/conf/spark-defaults.conf <<EOF
spark.jars.packages org.apache.spark:spark-connect_${SCALA_VERSION}:${SPARK_VERSION},io.delta:${DELTA_SCALA_ARTIFACT}:${DELTA_VERSION}
spark.jars.ivy ${SPARK_IVY_DIR}
spark.sql.extensions io.delta.sql.DeltaSparkSessionExtension
spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog
spark.sql.sources.default delta
spark.sql.catalogImplementation hive
spark.sql.warehouse.dir ${SPARK_STORE_DIR}/warehouse
spark.hadoop.javax.jdo.option.ConnectionURL jdbc:derby:;databaseName=${SPARK_STORE_DIR}/metastore_db;create=true
EOF

ARG MIGRATION_CAT
ARG MIGRATION_SCHEMA

# Re-attach stage 1's Delta tables to the persistent metastore. Runs through the
# same spark-defaults the server will use, so the tables are registered in the
# exact catalog clients will query. Derby creates metastore_db (and derby.log in
# the cwd) as root here, hence the chmod so `USER spark` and CI's --user 0:0 can
# both open it.
RUN --mount=type=bind,source=docker/spark-migrated/register_tables.py,target=/tmp/register_tables.py \
    cd /tmp \
    && /opt/spark/bin/spark-submit --master "local[1]" /tmp/register_tables.py \
        "${MIGRATION_CAT}" "${MIGRATION_SCHEMA}" "${SPARK_STORE_DIR}/warehouse" \
    && chmod -R 0777 "${SPARK_STORE_DIR}"

# Lets a consumer discover what was migrated without opening a session.
LABEL org.opencontainers.image.source="https://github.com/mcjug2015/cms_pipeline" \
      org.opencontainers.image.description="Spark Connect server pre-migrated to cms_pipeline's all_spark_migrations chain" \
      io.cms-pipeline.migrated.catalog="${MIGRATION_CAT}" \
      io.cms-pipeline.migrated.schema="${MIGRATION_SCHEMA}"

USER spark
EXPOSE 15002
CMD ["/opt/spark/sbin/start-connect-server.sh", "--wait"]
