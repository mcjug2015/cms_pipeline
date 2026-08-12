import os
from unittest import mock

from src.cms_pipeline.loader import TotOrigMeMaOhpEnroll

RES_DIR = os.path.join(os.path.dirname(__file__), "res")


@mock.patch(
    "src.cms_pipeline.loader.download_s3_zip",
    return_value=os.path.join(RES_DIR, "nested_total_enroll.zip"),
)
def test_load_total_enroll_inserts_year_rows_from_nested_zip(download_s3_zip, migrated_spark):
    # nested_total_enroll.zip holds MDCR ENROLL AB 1-8_CPS_02ENR_2023.zip, which holds a
    # standalone .xlsx of just the "MDCR ENROLL AB 1_CPS_02ENR" sheet trimmed to its header,
    # a BLANK row, the six year rows (2018-2023), and the trailing NOTES/SOURCE text rows —
    # exercising unwrap's zip-in-zip recursion and parse_sheet's BLANK/is_only_text_cell
    # filtering against real source data end to end.
    spark = migrated_spark[0]
    schema = migrated_spark[1]
    loader = TotOrigMeMaOhpEnroll()

    result = loader.load(spark, cat="spark_catalog", schema=schema)

    assert result == {"data_rows": 6}
    sql_result = spark.sql(
        f"select * from spark_catalog.{schema}.open_cms_data_kvp" " where sheet_name = 'MDCR ENROLL AB 1_CPS_02ENR';"
    )
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    # 6 year rows x 9 columns each
    assert len(results) == 54
    assert all(r["sheet_index"] == 0 for r in results)
    assert all(r["unzipped_name"] == "MDCR ENROLL AB 1-8_CPS_02ENR_2023.xlsx" for r in results)
    years = sorted({r["table_val"] for r in results if r["table_key"] == "Year"})
    assert years == ["2018", "2019", "2020", "2021", "2022", "2023"]
    # the KVP table has no per-row grouping id, so check the whole set of extracted
    # values for a column rather than trying to correlate a single row across keys
    total_enrollments = {r["table_val"] for r in results if r["table_key"] == "Total Enrollment"}
    assert total_enrollments == {
        "59989882.75002974",
        "61514510.08336582",
        "62840266.91670496",
        "63892625.83338015",
        "65100546.4167234",
        "66509868.8334003",
    }
    download_s3_zip.assert_called_once()
