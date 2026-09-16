#!/usr/bin/env bash
set -e

if [ "$#" -gt 0 ]; then
  echo "Usage: $0" >&2
  exit 1
fi

# Shared with the pre-commit hook: tests run against the pre-migrated Spark
# container, with no local embedded Spark fallback.
source "$(dirname "${BASH_SOURCE[0]}")/migrated_spark.sh"
require_docker

pants generate-lockfiles
pants lint check src/:: test/::

start_migrated_spark

# Unit tests run first, with coverage. Integration tests run afterward, as their own
# invocation, never in parallel with the unit run, and are excluded from --use-coverage —
# coverage should come only from unit tests (see CLAUDE.md "Laws of integration testing").
pants test --output=all --test-force --use-coverage --report test/:: -test/integration:: -- --durations=0
pants test --output=all --test-force --report test/integration:: -- --durations=0
