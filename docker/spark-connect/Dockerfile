# Test-only image: official Spark Connect image + Python 3.12.3 so the
# server-side UDF worker matches this repo's pinned interpreter
# (pants.toml [python] interpreter_constraints). Official apache/spark
# images only ship the base Ubuntu's Python (3.10 on 22.04/jammy), which
# fails PySpark's driver/worker minor-version check for any UDF test.
FROM apache/spark:4.1.0-scala2.13-java17-python3-ubuntu

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common gnupg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3.12 \
    && rm -rf /var/lib/apt/lists/*

ENV PYSPARK_PYTHON=/usr/bin/python3.12

USER spark
