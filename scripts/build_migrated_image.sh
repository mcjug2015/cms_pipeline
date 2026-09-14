#!/usr/bin/env bash
# Build the pre-migrated Spark Connect image (docker/spark-migrated/Dockerfile)
# and, with --push, export it to GHCR under the current branch's slug.
#
#   scripts/build_migrated_image.sh                    # build + tag locally
#   scripts/build_migrated_image.sh --push             # also push to GHCR
#   scripts/build_migrated_image.sh --push --latest    # also push :latest
#
# The tag is always the branch slug from scripts/branch_slug.sh -- the same slug
# the Databricks deployment and cleanup workflows key off, so a branch's image
# and its catalog stay recognizably paired. `--latest` additionally tags the same
# image `latest`. It is opt-in rather than inferred from being on main, so only
# CI's push-to-main run publishes `latest`, never a local build of a dirty tree.
#
# Pushing needs a prior `docker login ghcr.io` (CI does it with GITHUB_TOKEN;
# locally, a PAT with write:packages).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Overridable so a fork can publish under its own org without editing this file.
GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/mcjug2015/cms-pipeline-spark-migrated}"
BASE_IMAGE_TAG="${BASE_IMAGE_TAG:-spark-connect-test:4.1.0}"
LOCAL_IMAGE="${LOCAL_IMAGE:-cms-pipeline-spark-migrated}"

push=false
latest=false
for arg in "$@"; do
  case "$arg" in
    --push) push=true ;;
    --latest) latest=true ;;
    *)
      echo "usage: $(basename "$0") [--push] [--latest]" >&2
      exit 2
      ;;
  esac
done

branch="${GITHUB_REF_NAME:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)}"
slug="$(bash "$SCRIPT_DIR/branch_slug.sh" "$branch")"
echo "Branch '$branch' -> slug '$slug'" >&2

# The migrated image's final stage is FROM this, so it has to exist first. Same
# build as CI's "Build Spark Connect test image" step.
echo "Building base $BASE_IMAGE_TAG..." >&2
docker build -t "$BASE_IMAGE_TAG" "$REPO_ROOT/docker/spark-connect/"

# Context is the repo root: the migration chains under src/ are what get baked
# in. .dockerignore keeps that context to just those files.
tags=("$slug")
if [ "$latest" = true ]; then
  tags+=("latest")
fi

tag_args=(-t "$LOCAL_IMAGE:$slug")
for tag in "${tags[@]}"; do
  tag_args+=(-t "$GHCR_IMAGE:$tag")
done

echo "Building $LOCAL_IMAGE:$slug..." >&2
DOCKER_BUILDKIT=1 docker build \
  --build-arg "BASE_IMAGE=$BASE_IMAGE_TAG" \
  "${tag_args[@]}" \
  -f "$REPO_ROOT/docker/spark-migrated/Dockerfile" \
  "$REPO_ROOT"

if [ "$push" = true ]; then
  for tag in "${tags[@]}"; do
    echo "Pushing $GHCR_IMAGE:$tag..." >&2
    docker push "$GHCR_IMAGE:$tag"
    echo "Exported $GHCR_IMAGE:$tag" >&2
  done
else
  echo "Built $LOCAL_IMAGE:$slug with GHCR tags ${tags[*]} (not pushed; pass --push to export)" >&2
fi
