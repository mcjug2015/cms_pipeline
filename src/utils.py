import datetime
import logging
import os
import re
import uuid
from urllib.parse import urlparse

from pyspark.sql import DataFrame
from pyspark.sql.session import SparkSession

"""
TODO XXX get_ascending_letters_within_minute below shouldn't come from the lib,
move it somewhare saner
"""
from spark_sql_migrations.spark_sql.spark_sql import get_ascending_letters_within_minute

logger = logging.getLogger(__name__)


def convert_to_key(value: str) -> str:
    key = value.lower()
    key = re.sub(r"medicare\s+advantage", "ma", key)
    key = key.replace("medicare", "me")
    key = key.replace("year", "yr")
    key = key.replace("total", "tot")
    key = key.replace("enrollment", "enroll")
    key = key.replace("original", "orig")
    key = key.replace("percentage", "pct")
    key = key.replace("without", "wo")
    key = key.replace("count", "ct")
    key = key.replace("/", "_")
    return re.sub(r"\s+", "_", key)


def download_s3_zip(spark: SparkSession, s3_uri: str, dest_dir: str) -> str:
    parsed = urlparse(s3_uri)
    dest_path = os.path.join(dest_dir, os.path.basename(parsed.path))
    logger.info(f"downloading {s3_uri} -> {dest_path}")
    row = spark.read.format("binaryFile").load(s3_uri).select("content").first()
    assert row is not None
    with open(dest_path, "wb") as f:
        f.write(row["content"])
    return dest_path


def list_s3_files(spark: SparkSession, prefix_uri: str, name_glob: str) -> DataFrame:
    # Only the metadata columns are selected: binaryFile prunes `content`, so
    # this lists the prefix without pulling any file bodies back to the driver.
    logger.info(f"listing {prefix_uri} for {name_glob}")
    return (
        spark.read.format("binaryFile")
        .option("pathGlobFilter", name_glob)
        .load(prefix_uri)
        .select("path", "length", "modificationTime")
    )


def make_load_id() -> str:
    stamp = datetime.datetime.today().strftime("%Y%m%d_%H%M")
    return f"{stamp}_{get_ascending_letters_within_minute()}_{uuid.uuid4()}"
