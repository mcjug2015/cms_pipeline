import os
from unittest import mock

from src.harness.manipulator.loader import AbstractLoader

RES_DIR = os.path.join(os.path.dirname(__file__), "res")


@mock.patch.multiple(AbstractLoader, __abstractmethods__=set())
@mock.patch(
    "src.harness.manipulator.loader.convert_to_key", return_value="test converted key"
)
def test_insert_kvp_rows_success(convert_to_key, migrated_spark):
    spark = migrated_spark[0]
    schema = migrated_spark[1]
    loader = AbstractLoader("test inner file name")
    loader.insert_kvp_rows(
        spark,
        cat="spark_catalog",
        schema=schema,
        load_id="test_load_id",
        zip_name="test zip name",
        unzipped_name="test unzipped",
        sheet_name="test sheet name",
        sheet_index=0,
        data_rows=[{"test_key": "test_val"}],
    )
    sql_result = spark.sql(f"select * from spark_catalog.{schema}.open_cms_data_kvp;")
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    assert len(results) == 1
    assert results[0]["load_id"] == "test_load_id"
    assert results[0]["table_key"] == "test_key"
    assert results[0]["table_key_simple"] == "test converted key"
    assert results[0]["table_val"] == "test_val"
    convert_to_key.assert_called_once()


@mock.patch.multiple(AbstractLoader, __abstractmethods__=set())
def test_insert_kvp_rows_no_rows():
    loader = AbstractLoader("test inner file name")
    result = loader.insert_kvp_rows(
        None,
        cat=None,
        schema=None,
        load_id=None,
        zip_name=None,
        unzipped_name=None,
        sheet_name=None,
        sheet_index=0,
        data_rows=[],
    )
    assert result == 0


@mock.patch.multiple(AbstractLoader, __abstractmethods__=set())
@mock.patch(
    "src.harness.manipulator.loader.download_s3_zip", return_value="/i/am/not/real"
)
@mock.patch(
    "src.harness.manipulator.loader.AbstractLoader.get_s3_zip_uri",
    return_value="test_fake_s3_uri",
)
@mock.patch(
    "src.harness.manipulator.loader.Unwrapper.unwrap",
)
@mock.patch(
    "src.harness.manipulator.loader.AbstractLoader.parse_sheet",
    return_value=(77, [{"i am a fake": "data row"}]),
)
@mock.patch("src.harness.manipulator.loader.AbstractLoader.insert_kvp_rows")
def test_load_success(
    insert_kvp_rows, parse_sheet, unwrap, get_s3_zip_uri, download_s3_zip
):
    parse_sheet.return_value = (3, [{"test_key": "test_val"}])
    spark = mock.MagicMock(name="spark")
    unwrap.return_value.__enter__.return_value = "/fake/xlsx"

    loader = AbstractLoader("test inner file name")
    result = loader.load(spark, "test_cat", "test_schema")

    assert result["data_rows"] == 1
    insert_kvp_rows.assert_called_once()
    parse_sheet.assert_called_once()
    unwrap.assert_called_once()
    get_s3_zip_uri.assert_called_once()
    download_s3_zip.assert_called_once()


@mock.patch.multiple(AbstractLoader, __abstractmethods__=set())
@mock.patch(
    "src.harness.manipulator.loader.AbstractLoader.get_sheet_name",
    return_value="TestSheet",
)
@mock.patch(
    "src.harness.manipulator.loader.AbstractLoader.get_first_header_cell_val",
    return_value="Year",
)
def test_parse_sheet_returns_data_rows(get_first_header_cell_val, get_sheet_name):
    loader = AbstractLoader("test inner file name")

    sheet_index, data_rows = loader.parse_sheet(
        os.path.join(RES_DIR, "parse_sheet_sample.xlsx")
    )

    assert sheet_index == 0
    assert data_rows == [
        {"Year": "2023", "Metric": "TotalEnroll", "Value": "100"},
        {"Year": "2024", "Metric": "TotalEnroll", "Value": "200"},
    ]
    get_sheet_name.assert_called_once()
    # called once per header-scan row until the header ("Year") is matched
    assert get_first_header_cell_val.call_count == 2


@mock.patch.multiple(AbstractLoader, __abstractmethods__=set())
@mock.patch(
    "src.harness.manipulator.loader.AbstractLoader.get_sheet_name",
    return_value="TestSheet",
)
def test_parse_sheet_returns_no_rows(get_sheet_name):
    loader = AbstractLoader("test inner file name")

    sheet_index, data_rows = loader.parse_sheet(
        os.path.join(RES_DIR, "parse_sheet_no_rows_sample.xlsx")
    )

    assert sheet_index == 0
    assert data_rows == []
    get_sheet_name.assert_called_once()
