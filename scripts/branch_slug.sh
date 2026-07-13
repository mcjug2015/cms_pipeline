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

printf '%s\n' "$slug"
