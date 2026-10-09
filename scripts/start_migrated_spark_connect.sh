#!/usr/bin/env bash
# Replace the local migrated Spark container with a fresh one from the
# pre-migrated image (docker/spark-migrated, published to GHCR by CI).
# Meant to be sourced, via start_migrated_spark in migrated_spark.sh: exports
# SPARK_CONNECT_PORT and WHICH_SPARK=remote for the pants test runs that follow.
#
# Always a *fresh* container: whatever an earlier run left in a reused one
# (tables from half-finished tests, a newer migration chain from another branch)
# would otherwise leak into this run.
#
# It runs under a fixed name and host port and is left running afterwards, so
# one-off tests can use it later without looking anything up (validate.sh and
# pre-commit print how when they finish). The next run replaces it; stop it
# yourself with `docker rm -f cms-pipeline-spark-migrated`.
#
# Overrides:
#   MIGRATED_SPARK_IMAGE  image to run, e.g. a branch's slug tag. Must be
#                         pullable -- a failed pull is fatal, so a local-only
#                         build won't do.
#   MIGRATED_SPARK_PORT   host port, default 15002.
#
# Pulling the (private) GHCR image needs a prior `docker login ghcr.io`.

MIGRATED_SPARK_IMAGE="${MIGRATED_SPARK_IMAGE:-ghcr.io/mcjug2015/cms-pipeline-spark-migrated:latest}"
MIGRATED_SPARK_PORT="${MIGRATED_SPARK_PORT:-15002}"
MIGRATED_SPARK_CONTAINER=cms-pipeline-spark-migrated

# Pull before removing anything, so a failed pull leaves an already-running
# container alone instead of killing it for nothing.
echo "Pulling $MIGRATED_SPARK_IMAGE..." >&2
if ! docker pull "$MIGRATED_SPARK_IMAGE" >&2; then
  # No falling back to a local copy, even when one exists: it may predate the
  # latest migrations on main, and a run against it would pass or fail for the
  # wrong reasons.
  echo "ERROR: cannot pull $MIGRATED_SPARK_IMAGE." >&2
  echo "  Log in with: docker login ghcr.io -u mcjug2015" >&2
  echo "  Or point MIGRATED_SPARK_IMAGE at a pullable tag (see top of $(basename "${BASH_SOURCE[0]}"))." >&2
  return 1 2>/dev/null || exit 1
fi

# -a: a stopped container still holds the fixed name.
#
# Matched on the fixed *name*, not on the image: docker prints a bare image ID in
# `docker ps`'s Image column once the image a container was created from is no
# longer tagged, and the pull above is what untags it -- a new :latest leaves the
# previous one dangling. An image pattern therefore misses the container left by
# the previous run precisely when the published image has changed, and
# `docker run --name` below then fails with a name conflict.
#
# Matching this script's own container name also keeps the sweep off CI's: the
# self-hosted runner shares this machine's docker and runs this same migrated
# image deliberately unnamed (see ci.yml), so removing one would fail a CI job
# mid-test.
stale_spark_containers="$(docker ps -a --format '{{.ID}}\t{{.Names}}' |
  awk -v name="$MIGRATED_SPARK_CONTAINER" '$2 == name {print $1}')"
if [ -n "$stale_spark_containers" ]; then
  echo "Removing old migrated Spark container(s): $(echo "$stale_spark_containers" | tr '\n' ' ')" >&2
  # shellcheck disable=SC2086  # one ID per word, on purpose
  docker rm -f $stale_spark_containers >/dev/null
fi

# Same run shape as CI's "Start pre-migrated Spark Connect server" step: root, so the server
# can write into the mounted pytest tmp dir, which tests hand it paths inside. No
# --packages or ivy mount -- the image bakes its jars and Delta/metastore config
# in, and its default CMD starts the Connect server. Published on loopback only:
# Spark Connect has no auth, and a long-lived container shouldn't be reachable
# from the network.
echo "Starting $MIGRATED_SPARK_IMAGE as $MIGRATED_SPARK_CONTAINER on port $MIGRATED_SPARK_PORT..." >&2
SPARK_CONTAINER_ID="$(docker run -d \
  --name "$MIGRATED_SPARK_CONTAINER" \
  --user 0:0 \
  -p "127.0.0.1:$MIGRATED_SPARK_PORT:15002" \
  -v "$PYTEST_TMP_BASE:$PYTEST_TMP_BASE:rw" \
  "$MIGRATED_SPARK_IMAGE")"

if ! timeout 300 bash -c "
  until docker logs '$SPARK_CONTAINER_ID' 2>&1 | grep -q 'Spark Connect server started at:'; do
    docker ps -q --no-trunc | grep -q '$SPARK_CONTAINER_ID' || exit 1
    sleep 2
  done"; then
  echo "ERROR: Spark Connect server in $MIGRATED_SPARK_CONTAINER did not start; last log lines:" >&2
  docker logs --tail 30 "$SPARK_CONTAINER_ID" >&2 || true
  return 1 2>/dev/null || exit 1
fi

export SPARK_CONNECT_PORT="$MIGRATED_SPARK_PORT"
export WHICH_SPARK=remote
echo "Using SPARK_CONNECT_PORT=$SPARK_CONNECT_PORT from container $MIGRATED_SPARK_CONTAINER" >&2
