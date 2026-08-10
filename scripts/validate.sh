#!/usr/bin/env bash
set -e

pants generate-lockfiles
pants lint check src/ test/

SPARK_CONTAINER_ID=$(docker ps --format '{{.ID}}\t{{.Image}}' | awk '$2 ~ /^spark-connect-test/ {print $1; exit}')
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

pants test --output=all --test-force --use-coverage --report test/::