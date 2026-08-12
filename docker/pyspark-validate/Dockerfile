# syntax=docker/dockerfile:1
#
# Clones cms_pipeline fresh from GitHub and runs scripts/validate.sh against
# local embedded PySpark (no spark-connect-test container involved) — i.e.
# the same validation CI does, minus the "Verify Docker access" / "Build
# Spark Connect test image" / "Start Spark Connect server" steps. Since the
# docker CLI is deliberately not installed in this image,
# scripts/detect_spark_connect.sh always falls back to WHICH_SPARK=local
# (see that script), which is what puts validate.sh on the local-PySpark path.
#
#   DOCKER_BUILDKIT=1 docker build -t cms-pipeline-validate \
#     -f docker/pyspark-validate/Dockerfile docker/pyspark-validate
#
#   docker run --rm cms-pipeline-validate

FROM python:3.12.3-slim-bookworm

# Spark 4.1.0 (per test/requirements-dev.txt) needs a JVM; git clones the
# repo; curl bootstraps the pants launcher.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless \
        git \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 --retry 3 --retry-delay 2 --retry-all-errors \
        -fsSLo /tmp/get-pants.sh https://raw.githubusercontent.com/pantsbuild/setup/gh-pages/get-pants.sh \
    && bash /tmp/get-pants.sh \
    && rm /tmp/get-pants.sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
RUN git clone --depth 1 https://github.com/mcjug2015/cms_pipeline.git .

# pyspark's JVM subprocess just needs `java` on PATH, but some tooling checks
# JAVA_HOME explicitly; resolve it at runtime rather than hardcoding an arch-
# specific path (openjdk-17-jdk-headless installs under
# /usr/lib/jvm/java-17-openjdk-<arch>).
CMD ["bash", "-c", "export JAVA_HOME=\"$(dirname \"$(dirname \"$(readlink -f \"$(command -v java)\")\")\")\" && exec ./scripts/validate.sh"]
