#!/usr/bin/env bash
# The Spark setup validate.sh and the pre-commit hook share: tests always run
# against a fresh container from the pre-migrated image, brought up to this
# tree's migration chain. There is no local embedded Spark fallback.
#
# Meant to be sourced; it only defines functions, so sourcing it runs nothing:
#
#   source scripts/migrated_spark.sh
#   require_docker               # first, so a missing docker fails in seconds
#   ...lint, etc...
#   start_migrated_spark         # exports WHICH_SPARK / SPARK_CONNECT_PORT
#   ...pants test...
#
# start_migrated_spark sets an EXIT trap that prints how to reuse the container
# in one-off tests, so that's the last thing shown whether the tests pass or fail.
# A caller that needs its own EXIT trap should call print_migrated_spark_usage
# from it instead.

MIGRATED_SPARK_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_migrated_spark_usage() {
  cat >&2 <<EOF

Migrated Spark is still running as $MIGRATED_SPARK_CONTAINER (sc://localhost:$SPARK_CONNECT_PORT).
For one-off tests against it:
  WHICH_SPARK=remote SPARK_CONNECT_PORT=$SPARK_CONNECT_PORT PYTEST_TMP_BASE=$PYTEST_TMP_BASE \\
    pants test --test-force test/path/to/test_file.py
Outside pants (e.g. a REPL): SPARK_REMOTE=sc://localhost:$SPARK_CONNECT_PORT
Stop it with: docker rm -f $MIGRATED_SPARK_CONTAINER
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is required; tests run against a Spark Connect container" >&2
    exit 1
  fi
}

start_migrated_spark() {
  mkdir -p "$HOME/.cache/pytest-tmp"
  export PYTEST_TMP_BASE="$HOME/.cache/pytest-tmp"

  # Replace the migrated Spark container with a fresh one from the pre-migrated
  # image (main's migrations, already applied); see start_migrated_spark_connect.sh.
  # Not `source ... || return`: an `||` would switch off the caller's set -e for
  # everything inside the sourced file.
  source "$MIGRATED_SPARK_SCRIPT_DIR/start_migrated_spark_connect.sh"
  # Only once the container is actually up, so a failed start doesn't print
  # instructions for a container that isn't there.
  trap print_migrated_spark_usage EXIT

  # Then bring it up to *this* tree's chain: anything this branch added on top of
  # main gets applied incrementally, the way it will be on Databricks, and an
  # already-current chain proves a no-op re-run is clean.
  #
  # :spark-sql-migrations-local, not :spark-sql-migrations like CI's "Apply ddl"
  # step: that one resolves against databricks-connect, whose pyspark.dbutils makes
  # is_dbr() true and would send this to Databricks instead of the container.
  # Absolute --migrations-dir: pants runs the pex in a sandbox.
  SPARK_REMOTE="sc://${SPARK_CONNECT_HOST:-localhost}:$SPARK_CONNECT_PORT" \
    pants run src/crutch_migrations:spark-sql-migrations-local -- run \
      --migrations-dir="$(cd "$MIGRATED_SPARK_SCRIPT_DIR/.." && pwd)/src/crutch_migrations"
}
