#!/usr/bin/env bash
set -e

pants generate-lockfiles
pants lint check src/ test/

source "$(dirname "${BASH_SOURCE[0]}")/detect_spark_connect.sh"

# Unit tests run first, with coverage. Integration tests run afterward, as their own
# invocation, never in parallel with the unit run, and are excluded from --use-coverage —
# coverage should come only from unit tests (see CLAUDE.md "Laws of integration testing").
pants test --output=all --test-force --use-coverage --report test/:: -test/integration::
pants test --output=all --test-force --report test/integration::