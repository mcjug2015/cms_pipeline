#!/usr/bin/env bash
# Build (if needed) and start a spark-connect-test container for local test runs.
# Meant to be sourced by validate.sh, only after detect_spark_connect.sh has
# confirmed no spark-connect-test container is already running. Exports
# SPARK_CONNECT_PORT / WHICH_SPARK=remote like detect_spark_connect.sh does.
#
# Unlike CI (.github/workflows/ci.yml), the container is left running after
# the script exits, so subsequent local validate.sh runs can find it via
# detect_spark_connect.sh and reuse it instead of paying startup cost again.
# Stop it manually (`docker rm -f`) when you're done with it.

SPARK_IMAGE_TAG="spark-connect-test:4.1.0"
SPARK_IVY_CACHE_DIR="$HOME/.cache/spark-ivy"
SPARK_CONNECT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building $SPARK_IMAGE_TAG..." >&2
docker build -t "$SPARK_IMAGE_TAG" "$SPARK_CONNECT_SCRIPT_DIR/../docker/spark-connect/" >&2

mkdir -p "$SPARK_IVY_CACHE_DIR"
docker run --rm -v "$SPARK_IVY_CACHE_DIR:/ivy:rw" busybox \
  chown -R "$(id -u):$(id -g)" /ivy >&2
chmod -R 0777 "$SPARK_IVY_CACHE_DIR"

echo "Starting Spark Connect server container..." >&2
SPARK_CONTAINER_ID="$(docker run -d \
  --user 0:0 \
  -p 15002 \
  -v "$PYTEST_TMP_BASE:$PYTEST_TMP_BASE:rw" \
  -v "$SPARK_IVY_CACHE_DIR:/opt/spark/work-dir/ivy:rw" \
  "$SPARK_IMAGE_TAG" \
  /opt/spark/sbin/start-connect-server.sh \
    --wait \
    --packages org.apache.spark:spark-connect_2.13:4.1.0,io.delta:delta-spark_4.1_2.13:4.3.1 \
    --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
    --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
    --conf spark.sql.sources.default=delta \
    --conf spark.jars.ivy=/opt/spark/work-dir/ivy)"

timeout 600 bash -c \
  "until docker logs '$SPARK_CONTAINER_ID' 2>&1 | grep -q 'Spark Connect server started at:'; do sleep 2; done"

SPARK_CONNECT_PORT="$(docker inspect -f '{{(index (index .NetworkSettings.Ports "15002/tcp") 0).HostPort}}' "$SPARK_CONTAINER_ID")"
export SPARK_CONNECT_PORT
export WHICH_SPARK=remote
echo "Using SPARK_CONNECT_PORT=$SPARK_CONNECT_PORT from container $SPARK_CONTAINER_ID" >&2
