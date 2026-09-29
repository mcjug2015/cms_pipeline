import logging
import os
import shutil
from unittest import mock

from src.cms_pipeline.loader import load_new_zips

logger = logging.getLogger(__name__)
RES_DIR = os.path.join(os.path.dirname(__file__), "res")
FAKE_ZIP_URI = "s3://fake-bucket/fake-key.zip"


@mock.patch("src.cms_pipeline.loader.list_s3_files")
@mock.patch("src.cms_pipeline.loader.download_s3_zip")
def test_load_new_zips(download_s3_zip, list_s3_files, migrated_spark):
    spark = migrated_spark[0]
    schema = migrated_spark[1]

    def fake_download_s3_zip(_spark, _s3_uri, dest_dir):
        src_zip = os.path.join(RES_DIR, "nested_total_enroll.zip")
        dest_path = os.path.join(dest_dir, os.path.basename(src_zip))
        shutil.copy(src_zip, dest_path)
        return dest_path

    download_s3_zip.side_effect = fake_download_s3_zip
    list_s3_files.return_value = spark.createDataFrame([(FAKE_ZIP_URI,)], "path string")

    row_totals = load_new_zips(spark, "spark_catalog", schema, "s3://fake-bucket/")
    # Second pass over the same prefix: the ledger row written by the first pass
    # is what has to keep this from loading the zip again.
    replay_totals = load_new_zips(spark, "spark_catalog", schema, "s3://fake-bucket/")

    download_s3_zip.assert_called_once()
    list_s3_files.assert_called_with(spark, "s3://fake-bucket/", "*.zip")
    assert row_totals == {FAKE_ZIP_URI: 48}
    assert replay_totals == {}
    assert spark.table(f"spark_catalog.{schema}.open_cms_data_kvp").count() == 48

    ledger_rows = [r.asDict() for r in spark.table(f"spark_catalog.{schema}.open_cms_load_ledger").collect()]
    assert len(ledger_rows) == 1
    assert ledger_rows[0]["row_count"] == 48
