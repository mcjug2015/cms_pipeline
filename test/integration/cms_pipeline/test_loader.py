import logging
import os
import shutil
from unittest import mock

from src.cms_pipeline.loader import load_zip_workbook

logger = logging.getLogger(__name__)
RES_DIR = os.path.join(os.path.dirname(__file__), "res")


@mock.patch("src.cms_pipeline.loader.download_s3_zip")
def test_load_zip_workbook(download_s3_zip, migrated_spark):
    spark = migrated_spark[0]
    schema = migrated_spark[1]

    def fake_download_s3_zip(_spark, _s3_uri, dest_dir):
        src_zip = os.path.join(RES_DIR, "nested_total_enroll.zip")
        dest_path = os.path.join(dest_dir, os.path.basename(src_zip))
        shutil.copy(src_zip, dest_path)
        return dest_path

    download_s3_zip.side_effect = fake_download_s3_zip

    load_zip_workbook(
        spark,
        "spark_catalog",
        schema,
        "s3://fake-bucket/fake-key.zip",
    )

    download_s3_zip.assert_called_once()

    assert spark.table(f"spark_catalog.{schema}.open_cms_data_kvp").count() == 48
