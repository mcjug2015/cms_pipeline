import logging
import os
import shutil
from unittest import mock

from src.cms_pipeline.loader import load_cms_workbook, load_new_zips
from src.cms_pipeline.workbook_formats import open_workbook

logger = logging.getLogger(__name__)
RES_DIR = os.path.join(os.path.dirname(__file__), "res")
FAKE_ZIP_URI = "s3://fake-bucket/fake-key.zip"
CSV_NAME = "MDCR ENROLL AB 1_CPS_02ENR_2023.csv"
# The basename minus ".csv" is the single sheet a csv presents, at exactly the 31
# characters a sheet title allows, so nothing is truncated out of it.
CSV_SHEET_NAME = "MDCR ENROLL AB 1_CPS_02ENR_2023"


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


def test_load_cms_workbook_csv(migrated_spark):
    spark = migrated_spark[0]
    schema = migrated_spark[1]

    row_counts = load_cms_workbook(
        spark,
        "spark_catalog",
        schema,
        open_workbook(os.path.join(RES_DIR, CSV_NAME)),
        "placeholder.zip",
        CSV_NAME,
        "csv_test_load_id",
    )

    assert row_counts == {CSV_SHEET_NAME: 48}
    kvp_rows = [r.asDict() for r in spark.table(f"spark_catalog.{schema}.open_cms_data_kvp").collect()]
    assert len(kvp_rows) == 48
    total_enrollment_2018 = [
        r for r in kvp_rows if r["first_col_val"] == "2018" and r["table_key"] == "Total Enrollment"
    ]
    assert len(total_enrollment_2018) == 1
    # heading is blank because the only text-only row above the data is "BLANK",
    # which parse_sheet refuses as a heading.
    assert {
        "load_id": "csv_test_load_id",
        "zip_name": "placeholder.zip",
        "unzipped_name": CSV_NAME,
        "sheet_name": CSV_SHEET_NAME,
        "sheet_index": 0,
        "table_key": "Total Enrollment",
        "table_key_simple": "tot_enroll",
        "table_row_index": 0,
        "table_val": "59989882.75002974",
        "heading": "",
        "first_col_key": "Year",
        "first_col_val": "2018",
    }.items() <= total_enrollment_2018[0].items()
