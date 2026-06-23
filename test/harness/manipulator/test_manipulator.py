from test.utils import *

from src import custom_logging
from src.harness.manipulator.manipulator import with_spark

logger = custom_logging.setup_logging().getLogger(__name__)


def test_with_spark(migrated_spark):
    with_spark(migrated_spark, cat="spark_catalog", schema="default")
    sql_result = migrated_spark.sql(
        f"select * from spark_catalog.default.test_table order by int_id desc;"
    )
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    assert len(results) == 1
    assert results[0]["stuff"] == "zoop zoop"
    logger.info("end of test")
