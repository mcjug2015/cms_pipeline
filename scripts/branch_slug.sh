#!/usr/bin/env bash
# Map a git branch name to the sanitized slug used to isolate per-branch CI
# deployments
set -euo pipefail

branch="${1:-${GITHUB_REF_NAME:-}}"
# First whitespace-delimited token of the branch name.
slug="${branch%% *}"
# Lowercase; replace any char that isn't a letter/digit/underscore (e.g. '/').
slug="$(printf '%s' "$slug" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_')"
# Unity Catalog identifiers can't start with a digit; prefix if needed.
case "$slug" in [0-9]*) slug="b_${slug}" ;; esac
# Cap the final slug at 11 characters, b_ prefix included -- so a prefixed slug
# keeps 9 characters of the branch name and an unprefixed one keeps 11. Under this
# repo's YYMMDD_NN-description convention that leaves exactly b_YYMMDD_NN, so the
# date and sequence number are the whole of a slug's uniqueness: two branches that
# reuse a day's sequence number share one catalog, image tag and deployment.
slug="${slug:0:11}"

printf '%s\n' "$slug"
