#!/usr/bin/env bash
# Detect a locally running spark-connect-test container and export WHICH_SPARK /
# SPARK_CONNECT_PORT so local pants test runs share it instead of falling back to
# local embedded Spark. Meant to be sourced (`source scripts/detect_spark_connect.sh`),
# not executed, so the exports land in the caller's shell and are visible to every
# `pants test` invocation that follows — unit and integration alike.

SPARK_CONNECT_PORT=""
SPARK_CONTAINER_ID=""
if command -v docker >/dev/null 2>&1; then
  SPARK_CONTAINER_ID=$(docker ps --format '{{.ID}}\t{{.Image}}' 2>/dev/null | awk '$2 ~ /^spark-connect-test/ {print $1; exit}' || true)
fi
if [ -n "$SPARK_CONTAINER_ID" ]; then
  SPARK_CONNECT_PORT=$(docker inspect -f '{{(index (index .NetworkSettings.Ports "15002/tcp") 0).HostPort}}' "$SPARK_CONTAINER_ID" 2>/dev/null || true)
fi

if [ -z "$SPARK_CONTAINER_ID" ] || [ -z "$SPARK_CONNECT_PORT" ]; then
  echo "No running spark-connect-test container/port found; falling back to local Spark" >&2
  export WHICH_SPARK=local
else
  export SPARK_CONNECT_PORT
  export WHICH_SPARK=remote
  echo "Using SPARK_CONNECT_PORT=$SPARK_CONNECT_PORT from container $SPARK_CONTAINER_ID"
fi
