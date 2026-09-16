import datetime
import os
import random
import re
import string
import tempfile

import pytest  # type: ignore
from spark_sql_migrations import custom_logging
from spark_sql_migrations.spark_sql.spark_sql import (
    get_ascending_letters_within_minute,
    get_output_folder,
    run_migrations,
)
from spark_sql_migrations.spark_utils import get_spark

logger = custom_logging.setup_logging().getLogger(__name__)

# The parent of this project's migration chains, which spark_sql_migrations calls
# migrations_root. test/BUILD's test_utils depends on the chain resources, so
# they are in the sandbox at the same relative path as in the repo.
CRUTCH_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "src", "crutch_migrations"
)


def pytest_configure(config):
    # Pants overrides TMPDIR itself for every local test process (to keep temp
    # files inside its own sandbox root), so extra_env_vars can't use it.
    tmp_base = os.environ.get("PYTEST_TMP_BASE")
    if tmp_base:
        os.makedirs(tmp_base, exist_ok=True)
        tempfile.tempdir = tmp_base


@pytest.fixture(scope="session", autouse=True)
def _isolated_spark_storage(tmp_path_factory):
    if os.environ.get("WHICH_SPARK", "local") == "local":
        logger.info(
            f"WHICH_SPARK is local with value {os.environ.get('WHICH_SPARK', 'local')}; setting warehouse and"
            " metastore env vars"
        )
        base = tmp_path_factory.mktemp("spark_store")
        os.environ["SPARK_WAREHOUSE_DIR"] = str(base / "warehouse")
        os.environ["SPARK_METASTORE_DIR"] = str(base / "metastore_db")
    yield


@pytest.fixture(scope="session")
def _spark_connect_remote():
    """Point SPARK_REMOTE at the Spark Connect server on SPARK_CONNECT_PORT.
    Assumes it's already running (started separately, outside of pytest)."""
    if os.environ.get("WHICH_SPARK", "local") == "remote":
        logger.info(
            f"WHICH_SPARK is remote with value {os.environ.get('WHICH_SPARK', 'local')}; setting spark remote"
        )
        host = os.environ.get("SPARK_CONNECT_HOST", "localhost")
        port = os.environ.get("SPARK_CONNECT_PORT", 15002)
        os.environ["SPARK_REMOTE"] = f"sc://{host}:{port}"
    yield


# should be possible to isolate per test if needed
@pytest.fixture(scope="session")
def test_spark(_spark_connect_remote):
    yield get_spark()


def _migrate_schema(spark, schema):
    output_folder = get_output_folder(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_migrations_out")
    )
    run_migrations(
        spark,
        cat="spark_catalog",
        schema=schema,
        output_folder=output_folder,
        migrations_root=CRUTCH_MIGRATIONS_DIR,
    )


def _shallow_clone_schema(spark, source_schema, target_schema):
    """Stand target_schema up as shallow clones of source_schema's tables.

    Remote runs share one long-lived pre-migrated container, so the chain is already
    applied in `default`. A shallow clone is metadata only -- the clone reads the
    source's existing data files and writes any of its own -- so a per-test schema
    costs a few catalog calls instead of a chain replay. The state table comes along
    with it, which is what leaves the _migrate_schema call below a no-op check unless
    this branch adds migrations the image predates.
    """
    spark.sql(f"create schema if not exists spark_catalog.{target_schema}")
    for existing_table in spark.catalog.listTables(f"spark_catalog.{source_schema}"):
        if existing_table.isTemporary:
            continue
        spark.sql(
            f"create table spark_catalog.{target_schema}.`{existing_table.name}`"
            f" shallow clone spark_catalog.{source_schema}.`{existing_table.name}`"
        )


@pytest.fixture(scope="session")
def crutch_migrations_dir():
    yield CRUTCH_MIGRATIONS_DIR


@pytest.fixture(scope="function")
def migrated_spark(test_spark, request):
    module_slug = re.sub(r"\W+", "_", request.module.__name__)
    schema_name = f"b_{module_slug}"
    schema_name += f"_{datetime.datetime.today().strftime('%Y%m%d_%H%M')}"
    schema_name += f"_{get_ascending_letters_within_minute()}"
    schema_name += f"_{''.join(random.choices(string.ascii_letters, k=6))}"
    logger.info(
        f"WHICH_SPARK is {os.environ.get('WHICH_SPARK', 'local')}; using {schema_name} schema name"
        f" for module {request.module.__name__}"
    )
    if os.environ.get("WHICH_SPARK", "local") == "remote":
        _shallow_clone_schema(test_spark, "default", schema_name)
    _migrate_schema(test_spark, schema_name)
    yield (test_spark, schema_name)
