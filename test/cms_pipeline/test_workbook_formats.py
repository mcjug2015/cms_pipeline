import logging
from unittest import mock
from unittest.mock import MagicMock

import pytest  # type: ignore

from src.cms_pipeline.workbook_formats import (
    CsvSheet,
    CsvWorkbook,
    XlsxWorkbook,
    XlsxWorksheet,
    get_decimal_places,
    get_display_value,
    is_supported_workbook,
    open_workbook,
)

logger = logging.getLogger(__name__)


def test_csv_sheet_iter_rows(tmp_path):
    # min_row is 1-based and counts the header, so min_row=2 drops it and yields the
    # remaining rows as plain tuples of strings.
    csv_path = tmp_path / "claims.csv"
    csv_path.write_text("code,label\n001,alpha\n002,beta\n", encoding="utf-8")
    sheet = CsvSheet(str(csv_path), "claims")

    rows = list(sheet.iter_rows(min_row=2))

    assert rows == [("001", "alpha"), ("002", "beta")]


def test_csv_wkbk_trunk_path():
    workbook = CsvWorkbook("/data/extracts/a_very_long_cms_claims_extract_2024.csv")

    assert workbook.path == "/data/extracts/a_very_long_cms_claims_extract_2024.csv"
    assert workbook.sheetnames == ["a_very_long_cms_claims_extract_"]


@mock.patch("src.cms_pipeline.workbook_formats.CsvWorkbook.__init__", return_value=None)
def test_csv_wkbk_get_sheet_key_error(init):
    workbook = CsvWorkbook("claims.csv")
    workbook.path = "/data/claims.csv"
    workbook.sheetnames = ["claims"]

    with pytest.raises(KeyError, match="/data/claims.csv has no sheet named testing123"):
        workbook.get_sheet("testing123")

    init.assert_called_once()


@mock.patch("src.cms_pipeline.workbook_formats.CsvWorkbook.__init__", return_value=None)
def test_csv_wkbk_get_sheet_success(init):
    workbook = CsvWorkbook("claims.csv")
    workbook.path = "/data/claims.csv"
    workbook.sheetnames = ["testing123"]

    my_sheet = workbook.get_sheet("testing123")
    assert my_sheet.path == "/data/claims.csv"
    assert my_sheet.title == "testing123"

    init.assert_called_once()


def test_get_decimal_places_none_returns_none():
    result = get_decimal_places(None)

    assert result is None


def test_get_decimal_places_integer_format_returns_zero():
    result = get_decimal_places("#,##0")

    assert result == 0


def test_get_decimal_places_two_decimal_format_returns_two():
    result = get_decimal_places("#,##0.00")

    assert result == 2


def test_get_decimal_places_date_format_returns_none():
    result = get_decimal_places("yyyy-mm-dd")

    assert result is None


@mock.patch("src.cms_pipeline.workbook_formats.get_decimal_places")
def test_get_display_value_non_float_returns_value_unchanged(get_decimal_places):
    cell = mock.MagicMock(value="Alabama", number_format="General")

    result = get_display_value(cell)

    assert result == "Alabama"
    get_decimal_places.assert_not_called()


@mock.patch("src.cms_pipeline.workbook_formats.get_decimal_places", return_value=None)
def test_get_display_value_float_with_no_decimals_info_returns_value_unchanged(
    get_decimal_places,
):
    cell = mock.MagicMock(value=21324800.41667978, number_format="General")

    result = get_display_value(cell)

    assert result == 21324800.41667978
    get_decimal_places.assert_called_once_with("General")


@mock.patch("src.cms_pipeline.workbook_formats.get_decimal_places", return_value=0)
def test_get_display_value_float_with_zero_decimals_returns_rounded_int(
    get_decimal_places,
):
    cell = mock.MagicMock(value=21324800.41667978, number_format="#,##0")

    result = get_display_value(cell)

    assert result == 21324800
    assert isinstance(result, int)
    get_decimal_places.assert_called_once_with("#,##0")


@mock.patch("src.cms_pipeline.workbook_formats.get_decimal_places", return_value=2)
def test_get_display_value_float_with_nonzero_decimals_returns_rounded_float(
    get_decimal_places,
):
    cell = mock.MagicMock(value=21324800.4166, number_format="#,##0.00")

    result = get_display_value(cell)

    assert result == 21324800.42
    assert isinstance(result, float)
    get_decimal_places.assert_called_once_with("#,##0.00")


@mock.patch("src.cms_pipeline.workbook_formats.get_display_value", return_value="test")
def test_xlsx_sheet_iter_rows(get_display_value):
    sheet = MagicMock()
    sheet.iter_rows.return_value = [["cellA"], ["cellB"]]
    xlsx_sheet = XlsxWorksheet(sheet)

    rows = list(xlsx_sheet.iter_rows())

    assert rows == [("test",), ("test",)]
    sheet.iter_rows.assert_called_once_with(min_row=1)
    assert get_display_value.call_count == 2


@mock.patch("src.cms_pipeline.workbook_formats.XlsxWorkbook.__init__", return_value=None)
def test_xlsx_wkbk(init):
    wkbk = XlsxWorkbook()
    wkbk.workbook = {"key": "sheet"}
    assert wkbk.get_sheet("key").sheet == "sheet"
    init.assert_called_once()


def test_is_supported_workbook_matches_a_registered_extension_regardless_of_case():
    # Unwrapper feeds this bare zip entry names, which carry whatever case the
    # archive happened to use, so the match may not be case sensitive.
    assert is_supported_workbook("MDCR ENROLL AB 15-20_CPS_02ENR_2023.XLSX")


@mock.patch.dict(
    "src.cms_pipeline.workbook_formats.WORKBOOK_READERS",
    {".fake": lambda path: f"opened {path}"},
    clear=True,
)
def test_open_workbook_dispatches_to_the_reader_for_the_extension():
    result = open_workbook("/tmp/some_dir/thing.FAKE")

    assert result == "opened /tmp/some_dir/thing.FAKE"


@mock.patch.dict(
    "src.cms_pipeline.workbook_formats.WORKBOOK_READERS",
    {".fake": lambda path: f"opened {path}"},
    clear=True,
)
def test_open_workbook_raises_for_an_unregistered_extension():
    with pytest.raises(ValueError, match=r"no reader for \.nope files: /tmp/thing.nope"):
        open_workbook("/tmp/thing.nope")
